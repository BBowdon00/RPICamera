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
    body { 
        margin: 0; 
        padding: 0; 
        background: #000; 
        color: #fff; 
        font-family: Arial, sans-serif;
        overflow: hidden;
    }
    .container { 
        display: flex;
        flex-direction: column;
        height: 100vh;
        width: 100vw;
    }
    h1 { 
        margin: 0;
        padding: 10px;
        text-align: center;
        background: rgba(26, 26, 26, 0.8);
        font-size: 1.2em;
    }
    .stream-wrapper {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    img { 
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    .info {
        position: absolute;
        bottom: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.7);
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.9em;
    }
</style>
</head>
<body>
<div class="container">
    <h1>🌱 Hydroponic System - Live Camera Feed</h1>
    <div class="stream-wrapper">
        <img src="stream.mjpg" alt="Live Camera Stream" />
    </div>
    <div class="info">1920x1080 @ 30fps | Motion Detection Active</div>
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

                # Motion detection (only if enabled)
                motion_detected = False
                if self.motion_detector:
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
                
                # Convert frame and add timestamp
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

