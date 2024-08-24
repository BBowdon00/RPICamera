import os
import logging
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput, CircularOutput
from streaming import StreamingOutput, StreamingServer, StreamingHandler
from motion_detection import MotionDetector
from mqtt_handler import MqttHandler

def start_camera_server(config):
    # Paths and font setup
    save_path = os.path.expanduser("~/Camera/captured_images")
    os.makedirs(save_path, exist_ok=True)
    
    # Initialize components
    picamera2 = Picamera2()
    motion_detector = MotionDetector()
    mqtt_handler = MqttHandler(config.get('mqtt_broker'))

    if mqtt_handler:
        mqtt_handler.connect()

    picamera2.configure(picamera2.create_video_configuration(main={"size": (1280, 720)}))

    encoder = None
    if config.get('record_motion'):
        encoder = H264Encoder(bitrate=1000000)
        encoder.output = CircularOutput()
        picamera2.encoder = encoder

    output = StreamingOutput(encoder,motion_detector, mqtt_handler,config)
    picamera2.start_recording(MJPEGEncoder(bitrate=10000000), FileOutput(output))

    # Main loop to handle streaming
    try:
        port = config.get('server_port', 8000)
        address = ('', port)
        server = StreamingServer(address, StreamingHandler)
        server.output = output  # Pass the output to the server instance
        logging.info(f"Starting MJPEG server on {address[0]}:{address[1]}")
        server.serve_forever()
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
    finally:
        picamera2.stop_recording()
        if mqtt_handler:
            mqtt_handler.stop()

