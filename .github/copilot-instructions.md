# RPICamera - Raspberry Pi Camera Streaming & Motion Detection

## Project Overview
Camera streaming system for hydroponic monitoring with MJPEG streaming, motion detection, and MQTT integration. Runs on Raspberry Pi with Picamera2.

## Architecture
- **camera_server.py**: Main server orchestration, initializes components
- **streaming.py**: MJPEG HTTP server, frame processing pipeline
- **motion_detection.py**: Frame comparison motion detection (MSE-based)
- **mqtt_handler.py**: Publishes motion events to MQTT broker
- **config.py**: Command-line args + JSON config file parsing
- **utils.py**: Logging setup, timestamp overlay on frames
- **main.py**: Entry point

## Key Components

### Camera Server Flow
1. Initialize Picamera2 (1280x720)
2. Create motion detector + MQTT handler
3. Start MJPEG encoder with StreamingOutput
4. Run HTTP server on port 8000 (configurable)
5. Stream at `/stream.mjpg`, HTML page at `/`

### Motion Detection
- Uses MSE (Mean Squared Error) between frames
- Threshold: 7.0 (configurable)
- Optional bounding boxes with OpenCV contour detection
- Optional circular buffer H264 recording on motion

### MQTT Integration
- Client ID: "TentRPI"
- Topic: `camera/motion`
- Message: "Motion detected"
- Publishes on motion threshold exceeded

## Configuration
```json
{
  "record_motion": true,
  "bounding_box": true,
  "mqtt_broker": "192.168.1.100",
  "log_level": "INFO",
  "server_port": 8000
}
```

## Dependencies
- picamera2 (Raspberry Pi camera library) - [Official Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- paho-mqtt (MQTT client)
- opencv-python (cv2 for image processing)
- numpy (array operations)
- PIL/Pillow (image manipulation)

## Picamera2 Reference
- Official documentation: https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf
- GitHub repository: https://github.com/raspberrypi/picamera2

Key APIs used in this project:
- `Picamera2()` - Main camera object
- `create_video_configuration(main={"size": (width, height)})` - Configure video stream
- `start_recording(encoder, output)` - Begin recording to output
- `stop_recording()` - Stop recording
- `MJPEGEncoder(bitrate)` - JPEG motion encoder for streaming
- `H264Encoder(bitrate)` - H.264 encoder for recording
- `FileOutput(stream)` - Output to file-like object
- `CircularOutput()` - Circular buffer for motion-triggered recording

## Hardware Requirements
- Raspberry Pi (any model with camera support)
- Raspberry Pi Camera Module
- Font: `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`

## Common Tasks

### Running the Server
```bash
python3 src/main.py --config-file config.json --mqtt-broker 192.168.1.100
```

### Adjusting Motion Sensitivity
Edit `MotionDetector.__init__()` threshold parameter (lower = more sensitive)

### Adding New MQTT Topics
Modify `MqttHandler.publish_motion_event()` method

### Changing Video Resolution
Update `picamera2.create_video_configuration(main={"size": (WIDTH, HEIGHT)})`

## Code Patterns

### Error Handling
All components log errors but continue operation (resilient design)

### Threading
- HTTP server uses ThreadingMixIn for concurrent clients
- MQTT client runs in background thread (loop_start)
- Frame buffer uses threading.Condition for synchronization

### Frame Processing Pipeline
1. MJPEG encoder writes JPEG to StreamingOutput
2. Convert JPEG → PIL Image → numpy array
3. Run motion detection (grayscale comparison)
4. Draw bounding boxes if enabled
5. Overlay timestamp
6. Convert back to JPEG
7. Notify HTTP server threads

## Integration Notes
- Part of larger hydroponic monitoring system
- MQTT broker shared with ActuatorControl and Hydroponic_Monitor
- Camera feed viewable in Flutter mobile app
- Motion events trigger notifications in monitoring system

## Limitations
- Requires physical Raspberry Pi hardware (cannot run on desktop)
- picamera2 library is Pi-specific
- Motion detection is basic MSE (no ML/object detection)
- H.264 recording not fully integrated with persistence layer
