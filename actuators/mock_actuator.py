"""
Mock Actuator - Simulates physical actuator devices

This script consumes control commands from Kafka and simulates
the actions of physical actuators (pumps, valves, breakers, etc.)
"""

import json
import os
import sys
import time
from kafka import KafkaConsumer
from datetime import datetime
from collections import defaultdict

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
CONTROL_TOPIC = 'control-commands'

# Actuator state tracking
actuator_states = defaultdict(lambda: {'state': 'UNKNOWN', 'last_update': None})


def create_kafka_consumer():
    """Create and return a Kafka consumer for control commands."""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                CONTROL_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='mock-actuator-group'
            )
            print(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: Failed to connect: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Exiting.")
                sys.exit(1)


def simulate_actuator_action(command):
    """
    Simulate the physical action of an actuator.
    
    In a real SCADA system, this would interface with actual hardware
    through protocols like Modbus, OPC UA, or similar.
    """
    actuator_name = command.get('actuator')
    action = command.get('action')
    command_id = command.get('command_id')
    timestamp = command.get('timestamp')
    reason = command.get('reason', 'No reason provided')
    priority = command.get('priority', 'MEDIUM')
    
    print("\n" + "=" * 80)
    print(f"🔧 ACTUATOR ACTION")
    print("=" * 80)
    print(f"Command ID:  {command_id}")
    print(f"Timestamp:   {timestamp}")
    print(f"Actuator:    {actuator_name}")
    print(f"Action:      {action}")
    print(f"Priority:    {priority}")
    print(f"Reason:      {reason}")
    
    # Simulate different types of actuators
    if actuator_name.startswith('P-'):  # Pump
        simulate_pump(actuator_name, action)
    elif actuator_name.startswith('MV-'):  # Motorized Valve
        simulate_valve(actuator_name, action)
    elif actuator_name.startswith('ALERT'):  # Alert system
        simulate_alert(actuator_name, action)
    else:
        print(f"⚠️  Unknown actuator type: {actuator_name}")
        return False
    
    # Update actuator state
    actuator_states[actuator_name] = {
        'state': action,
        'last_update': timestamp,
        'last_command': command_id
    }
    
    print(f"✅ Action completed successfully")
    print("=" * 80)
    
    return True


def simulate_pump(pump_name, action):
    """Simulate pump operations."""
    print(f"💧 Pump Simulation: {pump_name}")
    
    if action == 'START':
        print(f"   ▶️  Starting pump {pump_name}")
        print(f"   🔄 Motor engaging...")
        time.sleep(0.5)  # Simulate startup delay
        print(f"   ✅ Pump running at nominal speed")
        print(f"   📊 Flow rate: Increasing to setpoint")
    
    elif action == 'STOP':
        print(f"   ⏸️  Stopping pump {pump_name}")
        print(f"   🔄 Motor disengaging...")
        time.sleep(0.3)  # Simulate shutdown delay
        print(f"   ✅ Pump stopped")
        print(f"   📊 Flow rate: 0.0 L/min")
    
    elif action == 'ADJUST_SPEED':
        print(f"   ⚙️  Adjusting pump speed")
        print(f"   🔄 Modifying variable frequency drive...")
        time.sleep(0.2)
        print(f"   ✅ Speed adjusted")
    
    else:
        print(f"   ⚠️  Unknown pump action: {action}")


def simulate_valve(valve_name, action):
    """Simulate motorized valve operations."""
    print(f"🚰 Valve Simulation: {valve_name}")
    
    if action == 'OPEN':
        print(f"   📖 Opening valve {valve_name}")
        print(f"   🔄 Actuator moving to OPEN position...")
        for i in range(0, 101, 20):
            time.sleep(0.1)
            print(f"   ↑  Position: {i}% open")
        print(f"   ✅ Valve fully opened")
        print(f"   📊 Flow: Unrestricted")
    
    elif action == 'CLOSE':
        print(f"   📕 Closing valve {valve_name}")
        print(f"   🔄 Actuator moving to CLOSED position...")
        for i in range(100, -1, -20):
            time.sleep(0.1)
            print(f"   ↓  Position: {i}% open")
        print(f"   ✅ Valve fully closed")
        print(f"   📊 Flow: Blocked")
    
    elif action == 'PARTIAL':
        position = 50  # Default to 50%
        print(f"   ⚙️  Adjusting valve to {position}% open")
        print(f"   🔄 Actuator moving to position...")
        time.sleep(0.2)
        print(f"   ✅ Valve positioned at {position}%")
    
    else:
        print(f"   ⚠️  Unknown valve action: {action}")


def simulate_alert(system_name, action):
    """Simulate alert system operations."""
    print(f"🔔 Alert System: {system_name}")
    
    if action == 'NOTIFY_OPERATOR':
        print(f"   📢 Sending notification to operator")
        print(f"   📧 Email notification sent")
        print(f"   📱 SMS alert sent")
        print(f"   🖥️  Dashboard alert triggered")
        print(f"   ✅ Operator notified")
    
    elif action == 'TRIGGER_ALARM':
        print(f"   🚨 ALARM TRIGGERED!")
        print(f"   🔊 Audible alarm activated")
        print(f"   💡 Visual indicators flashing")
        print(f"   📞 Emergency contact initiated")
    
    else:
        print(f"   ℹ️  Alert action: {action}")


def print_actuator_status():
    """Print status of all actuators."""
    if not actuator_states:
        print("\n📊 No actuator states recorded yet")
        return
    
    print("\n" + "=" * 80)
    print("📊 ACTUATOR STATUS SUMMARY")
    print("=" * 80)
    print(f"{'Actuator':<15} {'State':<15} {'Last Updated':<25} {'Command ID':<20}")
    print("-" * 80)
    
    for actuator, state_info in sorted(actuator_states.items()):
        last_update = state_info['last_update'] or 'N/A'
        command_id = state_info.get('last_command', 'N/A')
        print(f"{actuator:<15} {state_info['state']:<15} {last_update:<25} {command_id:<20}")
    
    print("=" * 80)


def main():
    """Main function to run the mock actuator."""
    print("=" * 80)
    print("🤖 NT-SCADA Mock Actuator System")
    print("=" * 80)
    print("This simulates physical actuators responding to control commands")
    print("-" * 80)
    
    # Create Kafka consumer
    consumer = create_kafka_consumer()
    
    print(f"👂 Listening to topic: {CONTROL_TOPIC}")
    print("-" * 80)
    
    command_count = 0
    success_count = 0
    
    try:
        for message in consumer:
            command_count += 1
            
            # Simulate actuator action
            success = simulate_actuator_action(message.value)
            
            if success:
                success_count += 1
            
            # Print status summary every 10 commands
            if command_count % 10 == 0:
                print_actuator_status()
                print(f"\n📈 Commands processed: {command_count}")
                print(f"✅ Successful actions: {success_count}")
                print(f"⚠️  Failed actions: {command_count - success_count}\n")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Mock actuator stopped by user")
        print_actuator_status()
        print(f"\n📊 Final statistics:")
        print(f"   Total commands: {command_count}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {command_count - success_count}")
    
    finally:
        consumer.close()
        print("👋 Mock actuator shut down gracefully")


if __name__ == "__main__":
    main()
