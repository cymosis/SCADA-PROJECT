"""
Simple Timer Producer for Real-time Analytics
Generates periodic events to trigger analytics processing
"""

import json
import time
import logging
from datetime import datetime
from kafka import KafkaProducer
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTimerProducer:
    """Simple timer producer for analytics"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.topic = 'scada.analytics-timer'
        self.producer = None
        self.running = False
        
    def connect(self):
        """Connect to Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def generate_timer_event(self):
        """Generate a timer event"""
        return {
            'event_type': 'analytics_timer',
            'timestamp': datetime.now().isoformat(),
            'trigger': 'periodic_analytics'
        }
    
    def start_producing(self, interval=30):
        """Start producing timer events"""
        if not self.producer and not self.connect():
            return False
        
        self.running = True
        logger.info(f"Starting analytics timer with {interval}s interval")
        
        try:
            while self.running:
                # Generate and send timer event
                timer_event = self.generate_timer_event()
                
                future = self.producer.send(self.topic, value=timer_event)
                record_metadata = future.get(timeout=10)
                
                logger.info(f"Analytics timer sent: {record_metadata.topic}:{record_metadata.offset}")
                
                # Wait for next interval
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Timer producer stopped")
        except Exception as e:
            logger.error(f"Error in timer producer: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the producer"""
        self.running = False
        if self.producer:
            self.producer.flush()
            self.producer.close()

def main():
    """Main function"""
    producer = SimpleTimerProducer()
    interval = int(os.getenv('ANALYTICS_INTERVAL', '30'))  # 30 seconds default
    
    logger.info(f"Starting real-time analytics timer (every {interval}s)")
    producer.start_producing(interval)

if __name__ == "__main__":
    main()
