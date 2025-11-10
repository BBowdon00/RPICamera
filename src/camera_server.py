import os
import logging
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput, CircularOutput, FfmpegOutput
from streaming import StreamingOutput, StreamingServer, StreamingHandler
from motion_detection import MotionDetector
from mqtt_handler import MqttHandler

def start_camera_server(config):
    # Initialize components
    picamera2 = Picamera2()
    
    # Only create motion detector if not disabled
    motion_detector = None
    if not config.get('disable_motion'):
        motion_detector = MotionDetector()
        logging.info("Motion detection enabled")
    else:
        logging.info("Motion detection disabled - streaming only mode")
    
    # Only create MQTT handler if broker address is provided and motion detection enabled
    mqtt_handler = None
    mqtt_broker = config.get('mqtt_broker')
    if mqtt_broker and not config.get('disable_motion'):
        mqtt_handler = MqttHandler(mqtt_broker)
        mqtt_handler.connect()

    # Determine streaming format
    stream_format = config.get('stream_format', 'hls')  # Default to HLS for better quality
    
    # Configure camera: 1080p main stream for viewing, 640x360 low-res for motion detection
    # Optimized for Camera Module 3 Wide viewing hydroponic greenhouse
    # For HLS, encode="main" to get H.264 from 1080p stream
    # For MJPEG, encode="lores" to process motion detection
    video_config = picamera2.create_video_configuration(
        main={"format": "RGB888", "size": (1920, 1080)},
        lores={"size": (640, 360), "format": "YUV420"},
        encode="main" if stream_format == 'hls' else "lores",
        controls={
            "FrameRate": 25,  # High framerate for smooth viewing (CPU available)
            # Autofocus - Camera Module 3 has motorized lens
            "AfMode": 2,  # Continuous autofocus (always active)
            "AfSpeed": 0,  # Normal speed - balanced and stable
            "AfRange": 0,  # Normal range (10cm to infinity) - good for whole plants
            # Exposure for grow lights (LED/HPS)
            "AeEnable": True,  # Auto exposure
            "ExposureTime": 0,  # Auto (adjust for flicker: 8333 for 120Hz, 10000 for 100Hz lights)
            "AnalogueGain": 1.0,  # Low gain for clean image
            # White balance for artificial grow lights - adjusted for blue tint
            "AwbEnable": True,
            "AwbMode": 3,  # Fluorescent mode - removes blue cast from LED grow lights
            # Image quality for plant observation
            "Brightness": 0.0,  # Neutral (-1.0 to 1.0)
            "Contrast": 1.1,  # Slightly increased for plant detail
            "Saturation": 1.0,  # Neutral (adjust if plants look too dull/vibrant)
            "Sharpness": 1.5,  # Increased sharpness to combat blur
            # Noise reduction
            "NoiseReductionMode": 1,  # Fast - good balance
        }
    )
    picamera2.configure(video_config)
    
    # Set up outputs based on streaming format
    hls_output = None
    mjpeg_output = None
    hls_output_dir = "/tmp/hls"
    
    if stream_format == 'hls':
        # HLS streaming with H.264 using FfmpegOutput
        # Create output directory
        os.makedirs(hls_output_dir, exist_ok=True)
        
        # Configure balanced LL-HLS for high quality with reasonable low latency
        low_latency = config.get('low_latency', False)
        
        if low_latency:
            # BALANCED LL-HLS: ~2-3 seconds latency with high quality
            hls_params = (
                f"-f hls "
                f"-hls_time 1.5 "                         # 1.5-second segments (sweet spot)
                f"-hls_list_size 3 "                      # Keep 3 segments (4.5s buffer)
                f"-hls_flags delete_segments+split_by_time+independent_segments "
                f"-hls_segment_type mpegts "               # MPEG-TS for better streaming
                f"-hls_allow_cache 0 "                    # No caching for live stream
                f"-g 38 "                                 # Keyframe every ~1.5s (38 frames at 25fps)
                f"-keyint_min 8 "                         # Minimum GOP for flexibility
                f"-sc_threshold 0 "                       # Consistent keyframe placement
                f"-preset fast "                          # Good speed/quality balance
                f"-tune film "                            # High quality for plant detail
                f"-profile:v high "                       # H.264 High Profile for better compression
                f"-level 4.1 "                           # Support up to 1080p efficiently
                f"-crf 18 "                              # High quality (lower = better, 18 = excellent)
                f"-maxrate 6M -bufsize 12M "             # Rate control for consistent quality
                f"-fflags +flush_packets "                # Reduce buffering delay
            )
        else:
            # STANDARD HIGH QUALITY: ~4-5 seconds latency, maximum quality
            hls_params = (
                f"-f hls "
                f"-hls_time 2 "                           # 2-second segments (stable)
                f"-hls_list_size 3 "                      # Keep 3 segments (6s buffer)
                f"-hls_flags delete_segments+split_by_time "
                f"-hls_allow_cache 0 "
                f"-g 50 "                                 # Keyframe every 2 seconds (50 frames at 25fps)
                f"-preset slow "                          # Maximum quality encoding
                f"-tune film "                            # Optimized for plant detail
                f"-profile:v high "                       # H.264 High Profile
                f"-level 4.1 "
                f"-crf 16 "                              # Very high quality (16 = near-lossless)
                f"-maxrate 8M -bufsize 16M "             # Higher bitrate for quality
            )
        
        hls_output = FfmpegOutput(f"{hls_params}{hls_output_dir}/stream.m3u8")
        logging.info("HLS streaming mode enabled (H.264 via FFmpeg)")
        if low_latency:
            logging.info("⚡ Balanced LL-HLS: ~2-3s latency with high quality")
            logging.info("💎 Quality: CRF 18 (excellent), 1.5s segments, 6M max bitrate")
            logging.info("� Features: Independent segments, MPEG-TS, fast preset")
        else:
            logging.info("🏆 Maximum Quality: ~4-5s latency, premium encoding")
            logging.info("💎 Quality: CRF 16 (near-lossless), 2s segments, 8M max bitrate")
            logging.info("⭐ Features: Slow preset for maximum quality")
        
        # Motion detection not yet supported in HLS mode
        if motion_detector:
            logging.warning("Motion detection not yet supported in HLS mode, disabling")
            motion_detector = None
    
    elif stream_format == 'mjpeg':
        # Original MJPEG streaming
        motion_encoder = None
        circular_output = None
        if config.get('record_motion'):
            motion_encoder = H264Encoder(bitrate=1000000)
            circular_output = CircularOutput(buffersize=100)
        
        mjpeg_output = StreamingOutput(motion_encoder, motion_detector, mqtt_handler, config, circular_output)
        logging.info("MJPEG streaming mode enabled")
    
    # Start encoders and recording
    if stream_format == 'hls':
        # Start H.264 HLS streaming on main stream
        # Higher bitrate for quality (CRF will control actual rate)
        bitrate = 6000000 if low_latency else 8000000  # 6-8 Mbps max for high quality
        hls_encoder = H264Encoder(bitrate=bitrate)
        picamera2.start_recording(hls_encoder, hls_output)
    
    elif stream_format == 'mjpeg':
        # Start motion recording encoder if enabled
        if config.get('record_motion') and mjpeg_output.encoder:
            picamera2.start_encoder(mjpeg_output.encoder, circular_output)
        
        # Start MJPEG streaming
        mjpeg_encoder = MJPEGEncoder(bitrate=20000000)
        picamera2.start_recording(mjpeg_encoder, FileOutput(mjpeg_output))
    
    # Note: Continuous autofocus (AfMode=2) runs automatically
    logging.info(f"Camera started with continuous autofocus ({stream_format} streaming)")

    # Main loop to handle streaming
    try:
        port = config.get('server_port', 8000)
        address = ('', port)
        server = StreamingServer(address, StreamingHandler)
        
        # Pass appropriate outputs to server
        server.hls_output_dir = hls_output_dir if stream_format == 'hls' else None
        server.mjpeg_output = mjpeg_output
        server.stream_format = stream_format
        
        logging.info(f"Starting streaming server on {address[0]}:{address[1]} ({stream_format} mode)")
        server.serve_forever()
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
    finally:
        # Stop all encoders
        picamera2.stop_recording()
        
        # Close HLS output if active
        if hls_output:
            hls_output.close()
        
        # Cleanup MQTT
        if mqtt_handler:
            mqtt_handler.stop()
            mqtt_handler.disconnect()

