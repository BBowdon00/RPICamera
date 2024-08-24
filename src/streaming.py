import io
import logging
import socketserver
import numpy as np
import cv2
from http import server
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput, CircularOutput
from PIL import Image,ImageFont
from motion_detection import MotionDetector
from utils import overlay_timestamp
import os

# HTML page for the server
PAGE = """
<html>
<head>
<title>Picamera2 MJPEG Streaming Demo with Timestamp</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming Demo with Timestamp</h1>
<img src="stream.mjpg" width="1280" height="720" />
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self, encoder, motion_detector, mqtt_handler, config):
        
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            logging.error(f"Font not found at {font_path}. Exiting.")
            return
        self.font = ImageFont.truetype(font_path, 24)
        self.encoder = encoder
        self.frame = None
        self.condition = Condition()
        self.motion_detector = motion_detector
        self.mqtt_handler = mqtt_handler
        self.draw_bbox = config.get("bounding_box")
        self.record_motion =  config.get("record_motion")

    def write(self, buf):
        with self.condition:
            try:
                img = Image.open(io.BytesIO(buf))
                frame = np.array(img)

                # Motion detection
                motion_detected, gray = self.motion_detector.detect_motion(frame)
                if motion_detected:
                    if self.mqtt_handler:
                        self.mqtt_handler.publish_motion_event()

                    if self.draw_bbox:
                        frame = self.motion_detector.draw_bounding_boxes(frame, gray)

                    if self.record_motion:
                        self.encoder.output.start()
                        logging.info("Started recording due to motion detection")

                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img = overlay_timestamp(img, self.font)
                output = io.BytesIO()
                img.save(output, format="JPEG")
                self.frame = output.getvalue()
                self.condition.notify_all()

            except Exception as e:
                logging.error(f"Error processing frame: {e}")

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(PAGE.encode('utf-8'))
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with self.server.output.condition:
                        self.server.output.condition.wait()
                        frame = self.server.output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(f"Removed streaming client {self.client_address}: {e}")
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.output = None

