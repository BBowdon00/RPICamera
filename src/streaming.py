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
from motion_recorder import MotionRecorder
from motion_detection import MotionDetector
from utils import overlay_timestamp
import os

# HTML page for the server
PAGE = """
<html>
<head>
<title>Hydroponic System Camera Feed</title>
<style>
    body { margin: 0; padding: 20px; background: #1a1a1a; color: #fff; font-family: Arial, sans-serif; }
    h1 { text-align: center; }
    .container { max-width: 1920px; margin: 0 auto; text-align: center; }
    img { max-width: 100%; height: auto; border: 2px solid #444; border-radius: 8px; }
</style>
</head>
<body>
<div class="container">
    <h1>🌱 Hydroponic System - Live Camera Feed</h1>
    <img src="stream.mjpg" alt="Live Camera Stream" />
    <p>Resolution: 1920x1080 @ 30fps | Motion Detection Active</p>
</div>
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self, encoder, motion_detector, mqtt_handler, config, circular_output=None):
        
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            logging.error(f"Font not found at {font_path}.")
            raise FileNotFoundError(f"Required font not found at {font_path}")
        self.font = ImageFont.truetype(font_path, 24)
        self.encoder = encoder
        self.frame = None
        self.condition = Condition()
        self.motion_detector = motion_detector
        self.mqtt_handler = mqtt_handler
        self.draw_bbox = config.get("draw_box")
        self.record_motion = config.get("record_motion")
        
        # Only create recorder if encoder and circular output exist (recording is enabled)
        self.recorder = None
        if circular_output and self.record_motion:
            self.recorder = MotionRecorder(
                encoder_output=circular_output,
                save_dir=os.path.expanduser("~/Camera/captured_images"),
                timeout=2,
                buffer_seconds=3
            )

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
                
                # Always update reference frame to adapt to gradual changes
                self.motion_detector.update_reference(gray)
                
                # Update recorder if it exists
                if self.recorder:
                    self.recorder.update(motion_detected)
                img = Image.fromarray(frame)
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
                    # Write multipart boundary and headers directly to socket
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
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

