import os
import logging
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput, CircularOutput
from streaming import StreamingOutput, StreamingServer, StreamingHandler
from motion_detection import MotionDetector
from mqtt_handler import MqttHandler

def start_camera_server(config):
    # Initialize components
    picamera2 = Picamera2()
    motion_detector = MotionDetector()
    
    # Only create MQTT handler if broker address is provided
    mqtt_handler = None
    mqtt_broker = config.get('mqtt_broker')
    if mqtt_broker:
        mqtt_handler = MqttHandler(mqtt_broker)
        mqtt_handler.connect()

    # Configure camera: 1080p main stream for viewing, 640x360 low-res for motion detection
    video_config = picamera2.create_video_configuration(
        main={"format": "RGB888", "size": (1920, 1080)},
        lores={"size": (640, 360), "format": "YUV420"},
        encode="lores",
        controls={"FrameRate": 20}
    )
    picamera2.configure(video_config)
    
    # Set up encoder for motion recording if enabled
    encoder = None
    circular_output = None
    if config.get('record_motion'):
        encoder = H264Encoder(bitrate=1000000)
        circular_output = CircularOutput(buffersize=100)
        # Note: encoder.output will be set to circular_output when start_encoder is called
    
    picamera2.set_controls({"AwbEnable": True})
    
    # Create streaming output (will handle motion recording internally)
    output = StreamingOutput(encoder, motion_detector, mqtt_handler, config, circular_output)
    
    # Start MJPEG streaming (and H264 encoder if enabled)
    if config.get('record_motion'):
        picamera2.start_encoder(encoder, circular_output)
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
        if config.get('record_motion') and encoder:
            picamera2.stop_encoder(encoder)
        if mqtt_handler:
            mqtt_handler.stop()
            mqtt_handler.disconnect()

