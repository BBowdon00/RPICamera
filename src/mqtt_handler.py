import paho.mqtt.client as mqtt
import logging

class MqttHandler:
    def __init__(self, broker_address):
        self.client = mqtt.Client()
        self.broker_address = broker_address

    def connect(self):
        try:
            self.client.connect(self.broker_address)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
            return False
        return True

    def publish_motion_event(self, topic="camera/motion", message="Motion detected"):
        try:
            self.client.publish(topic, message)
        except Exception as e:
            logging.error(f"Failed to publish MQTT message: {e}")

    def stop(self):
        self.client.loop_stop()

    def disconnect(self):
        try:
            self.client.disconnect()
            self.stop()
        except Exception as e:
            logging.error(f"Error during MQTT disconnect: {e}")


