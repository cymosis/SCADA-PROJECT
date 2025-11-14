"""
Control Producer - Generates control commands for actuators

This script monitors anomalies and generates appropriate control
commands to be sent to actuators (valves, pumps, breakers, etc.)
"""

import json
import os
import sys
import time
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
ANOMALY_TOPIC = 'anomalies'
CONTROL_TOPIC = 'control-commands'


def create_kafka_consumer():
    """Create and return a Kafka consumer for anomalies."""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                ANOMALY_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='control-processor-group'
            )
            print(f"✅ Connected to Kafka consumer at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: Failed to connect: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Exiting.")
                sys.exit(1)


def create_kafka_producer():
    """Create and return a Kafka producer for control commands."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        print(f"✅ Connected to Kafka producer at {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except Exception as e:
        print(f"❌ Failed to create producer: {e}")
        sys.exit(1)


def generate_control_commands(anomaly_message):
    """
    Generate appropriate control commands based on the anomaly detected.
    
    This is a simplified control logic. In a real SCADA system, this would
    involve complex decision-making, safety checks, and operator approval.
    """
    commands = []
    
    try:
        timestamp = anomaly_message.get('timestamp')
        anomaly_class = anomaly_message.get('anomaly_class', 'Unknown')
        confidence = anomaly_message.get('confidence', 0.0)
        sensors = anomaly_message.get('sensors', {})
        
        # Control logic based on anomaly type
        # These are example rules - customize based on your SWaT understanding
        
        if confidence > 0.8:  # High confidence anomaly
            # Example: If flow sensor shows anomaly, adjust related pump
            for sensor_name, value in sensors.items():
                if sensor_name.startswith('FIT-'):
                    # Extract stage number (e.g., FIT-101 -> stage 1)
                    try:
                        stage = int(sensor_name.split('-')[1][0])
                        pump_name = f"P-{stage}01"
                        
                        # Generate command to adjust pump
                        command = {
                            'command_id': f"CMD-{int(time.time() * 1000)}",
                            'timestamp': datetime.utcnow().isoformat(),
                            'actuator': pump_name,
                            'action': 'STOP' if value > 4 else 'START',
                            'reason': f"Anomaly in {sensor_name}: {anomaly_class}",
                            'confidence': confidence,
                            'priority': 'HIGH' if confidence > 0.9 else 'MEDIUM'
                        }
                        commands.append(command)
                    except:
                        pass
                
                # Example: If level sensor shows anomaly, adjust motorized valve
                elif sensor_name.startswith('LIT-'):
                    try:
                        stage = int(sensor_name.split('-')[1][0])
                        valve_name = f"MV-{stage}01"
                        
                        command = {
                            'command_id': f"CMD-{int(time.time() * 1000)}",
                            'timestamp': datetime.utcnow().isoformat(),
                            'actuator': valve_name,
                            'action': 'CLOSE' if value > 900 else 'OPEN',
                            'reason': f"Anomaly in {sensor_name}: {anomaly_class}",
                            'confidence': confidence,
                            'priority': 'HIGH' if confidence > 0.9 else 'MEDIUM'
                        }
                        commands.append(command)
                    except:
                        pass
        
        # If no specific commands generated, create a general alert command
        if not commands:
            command = {
                'command_id': f"CMD-{int(time.time() * 1000)}",
                'timestamp': datetime.utcnow().isoformat(),
                'actuator': 'ALERT_SYSTEM',
                'action': 'NOTIFY_OPERATOR',
                'reason': f"Anomaly detected: {anomaly_class}",
                'confidence': confidence,
                'priority': 'LOW'
            }
            commands.append(command)
    
    except Exception as e:
        print(f"⚠️  Error generating control commands: {e}")
    
    return commands


def process_anomaly(anomaly_message, producer):
    """Process an anomaly message and generate control commands."""
    try:
        # Generate control commands
        commands = generate_control_commands(anomaly_message)
        
        # Send each command to the control topic
        for command in commands:
            producer.send(CONTROL_TOPIC, value=command)
            print(f"📤 Control Command: {command['actuator']} -> {command['action']}")
            print(f"   Reason: {command['reason']}")
            print(f"   Priority: {command['priority']}")
            print("-" * 60)
        
        return len(commands)
    
    except Exception as e:
        print(f"❌ Error processing anomaly: {e}")
        return 0


def main():
    """Main function to run the control processor."""
    print("=" * 80)
    print("🎛️  NT-SCADA Control Processor")
    print("=" * 80)
    
    # Create Kafka consumer and producer
    consumer = create_kafka_consumer()
    producer = create_kafka_producer()
    
    print(f"👂 Listening to topic: {ANOMALY_TOPIC}")
    print(f"📤 Publishing to topic: {CONTROL_TOPIC}")
    print("-" * 80)
    
    anomaly_count = 0
    command_count = 0
    
    try:
        for message in consumer:
            anomaly_count += 1
            
            print(f"\n🚨 ANOMALY #{anomaly_count} DETECTED")
            print(f"Time: {message.value.get('timestamp')}")
            print(f"Class: {message.value.get('anomaly_class')}")
            print(f"Confidence: {message.value.get('confidence', 0):.2f}")
            
            # Generate and send control commands
            commands_generated = process_anomaly(message.value, producer)
            command_count += commands_generated
            
            # Print statistics
            if anomaly_count % 10 == 0:
                print(f"\n📊 Statistics:")
                print(f"   Anomalies processed: {anomaly_count}")
                print(f"   Commands generated: {command_count}")
                print(f"   Avg commands/anomaly: {command_count/anomaly_count:.2f}")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Control processor stopped by user")
        print(f"📊 Final stats: {anomaly_count} anomalies, {command_count} commands generated")
    
    finally:
        producer.flush()
        producer.close()
        consumer.close()
        print("👋 Control processor shut down gracefully")


if __name__ == "__main__":
    main()
