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
- Raspberry Pi 4 (recommended) or Pi 3B+
- **Raspberry Pi Camera Module 3 Wide** (imx708_wide sensor)
  - Has autofocus (motorized lens) - major upgrade from Module 2
  - Wide angle lens (120° diagonal FOV) ideal for greenhouse coverage
  - 11.9MP sensor, HDR support
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

### Camera Module 3 Wide Autofocus Settings
The system is configured for continuous autofocus optimized for greenhouse monitoring.

**Autofocus Controls** (in `camera_server.py` video_config):
- **AfMode**: 0=Manual, 1=Auto (single shot), 2=Continuous (currently set)
  - **Continuous mode** (2): Automatically refocuses continuously - no AfTrigger needed
  - **Auto mode** (1): Single focus cycle - requires AfTrigger=0 after start()
  - **Manual mode** (0): Uses LensPosition control (0.0=infinity, 10.0=10cm)
- **AfSpeed**: 0=Normal (current), 1=Fast
  - Normal provides stable, smooth focusing without hunting
  - Fast for rapid-fire still captures
- **AfRange**: 0=Normal (10cm-∞), 1=Macro (<10cm), 2=Full
  - Normal is ideal for whole plant viewing
  - Use Macro if camera is very close for leaf detail
- **AfTrigger**: 0=Start AF, 1=Cancel
  - **Only used with Auto mode (AfMode=1)** to start a single focus cycle
  - Not needed for Continuous mode - it runs automatically
  - Must be called after `start()` or `start_recording()`, not after `configure()`

**Exposure & White Balance for Grow Lights:**
- **AwbMode**: 0=Auto (current), 1=Incandescent, 2=Tungsten, 3=Fluorescent, 4=Indoor, 5=Daylight
  - Try mode 1 (Incandescent) if colors look purple/pink under LED grow lights
  - Try mode 3 (Fluorescent) for white/cool LED lights
- **ExposureTime**: 0=Auto (current)
  - Set to 8333µs to eliminate 120Hz flicker (North America AC)
  - Set to 10000µs to eliminate 100Hz flicker (Europe/Asia AC)
  - Helps prevent banding/flicker from LED drivers

**Image Quality Tuning:**
- **Contrast**: 1.1 (slightly boosted for plant detail)
- **Saturation**: 1.0 (neutral - increase to 1.2 for more vibrant greens)
- **Sharpness**: 1.2 (enhanced for leaf edges and texture)
- **Brightness**: 0.0 (adjust ±0.2 if image too dark/bright)

**Common Scenarios:**
1. **Plants look washed out**: Increase Saturation to 1.2-1.3
2. **Purple/pink color cast**: Change AwbMode to 1 (Incandescent)
3. **Flickering/banding visible**: Set ExposureTime to 8333 or 10000
4. **Too blurry/soft**: Increase Sharpness to 1.5-2.0
5. **Close-up inspection**: Change AfRange to 1 (Macro mode)

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
