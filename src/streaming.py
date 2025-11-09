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
HLS_PAGE = """
<html>
<head>
<title>Hydroponic System Camera Feed (HLS)</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
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
        position: relative;
    }
    video { 
        width: 100%;
        height: 100%;
        object-fit: contain;
        background: #000;
    }
    .info {
        position: absolute;
        bottom: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.7);
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.9em;
        z-index: 10;
    }
    .fullscreen-btn {
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid #fff;
        color: #fff;
        padding: 8px 15px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9em;
        z-index: 10;
    }
    .fullscreen-btn:hover {
        background: rgba(50, 50, 50, 0.9);
    }
    .status {
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(0, 0, 0, 0.7);
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.8em;
        z-index: 10;
    }
    .status.loading { color: #ffa500; }
    .status.playing { color: #00ff00; }
    .status.error { color: #ff0000; }
</style>
<script>
    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    document.addEventListener('DOMContentLoaded', function() {
        var video = document.getElementById('video');
        var status = document.getElementById('status');
        var videoSrc = '/stream.m3u8';
        
        if (Hls.isSupported()) {
            var hls = new Hls({
                maxBufferLength: 10,
                maxMaxBufferLength: 30,
                maxBufferSize: 60 * 1000 * 1000,
                maxBufferHole: 0.5,
                lowLatencyMode: true,
                backBufferLength: 0
            });
            
            hls.loadSource(videoSrc);
            hls.attachMedia(video);
            
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                status.textContent = '● LIVE';
                status.className = 'status playing';
                video.play();
            });
            
            hls.on(Hls.Events.ERROR, function(event, data) {
                if (data.fatal) {
                    status.textContent = '● ERROR';
                    status.className = 'status error';
                    console.error('HLS error:', data);
                }
            });
        }
        // Native HLS support (Safari, iOS)
        else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = videoSrc;
            video.addEventListener('loadedmetadata', function() {
                status.textContent = '● LIVE';
                status.className = 'status playing';
                video.play();
            });
        }
        
        status.textContent = '● Loading...';
        status.className = 'status loading';
    });
</script>
</head>
<body>
<div class="container">
    <h1>🌱 Hydroponic System - Live Camera Feed (H.264 HLS)</h1>
    <div class="stream-wrapper">
        <div id="status" class="status">● Loading...</div>
        <button class="fullscreen-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
        <video id="video" autoplay muted playsinline></video>
    </div>
    <div class="info">1920x1080 @ 30fps | H.264 Streaming | Motion Detection Active</div>
</div>
</body>
</html>
"""

PAGE = """
<html>
<head>
<title>Hydroponic System Camera Feed (MJPEG)</title>
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
        position: relative;
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
        z-index: 10;
    }
    .fullscreen-btn {
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid #fff;
        color: #fff;
        padding: 8px 15px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9em;
        z-index: 10;
    }
    .fullscreen-btn:hover {
        background: rgba(50, 50, 50, 0.9);
    }
</style>
<script>
    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
</script>
</head>
<body>
<div class="container">
    <h1>🌱 Hydroponic System - Live Camera Feed</h1>
    <div class="stream-wrapper">
        <button class="fullscreen-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
        <img src="stream.mjpg" alt="Live Camera Stream" />
    </div>
    <div class="info">1920x1080 @ 30fps | Motion Detection Active</div>
</div>
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self, encoder, motion_detector, mqtt_handler, config, circular_output=None, for_motion_only=False):
        
        self.for_motion_only = for_motion_only  # If True, don't serve to clients
        
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
        self.draw_bbox = config.get("draw_box") if not for_motion_only else False
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
            # Serve appropriate HTML page based on stream format
            page_content = HLS_PAGE if self.server.stream_format == 'hls' else PAGE
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(page_content.encode('utf-8'))
        
        elif self.path == '/stream.mjpg':
            # MJPEG stream
            if not self.server.mjpeg_output:
                self.send_error(404)
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with self.server.mjpeg_output.condition:
                        self.server.mjpeg_output.condition.wait()
                        frame = self.server.mjpeg_output.frame
                    # Write multipart boundary and headers directly to socket
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(f"Removed streaming client {self.client_address}: {e}")
        
        elif self.path == '/stream.m3u8':
            # HLS playlist
            if not self.server.hls_manager:
                self.send_error(404)
                self.end_headers()
                return
            
            playlist_content = self.server.hls_manager.generate_playlist()
            if not playlist_content:
                self.send_error(503)
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(playlist_content.encode('utf-8'))
        
        elif self.path.endswith('.ts'):
            # HLS segment
            if not self.server.hls_manager:
                self.send_error(404)
                self.end_headers()
                return
            
            filename = os.path.basename(self.path)
            segment_path = self.server.hls_manager.get_segment_path(filename)
            
            if not os.path.exists(segment_path):
                self.send_error(404)
                self.end_headers()
                return
            
            try:
                with open(segment_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'max-age=10')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                logging.error(f"Error serving segment {filename}: {e}")
                self.send_error(500)
                self.end_headers()
        
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.mjpeg_output = None
        self.hls_manager = None
        self.stream_format = 'mjpeg'

