
# Hydroponic System - Camera Streaming and Motion Detection

## Overview
Real-time camera monitoring system for hydroponic grow environments using Raspberry Pi Camera and Picamera2 library. Features 1080p MJPEG streaming, motion detection with optional bounding boxes, H.264 recording on motion events, and MQTT integration for system alerts.

## Features
- **1080p MJPEG streaming** @ 30fps via HTTP
- **Motion detection** using efficient low-res stream (640x360) with adjustable sensitivity
- **H.264 circular buffer recording** - automatically saves clips when motion detected
- **MQTT integration** for event notifications to other system components
- **Timestamp overlay** on streaming video
- **Multi-client support** - multiple viewers can connect simultaneously
- **Configurable** via command-line arguments and JSON configuration file

## Hardware Requirements
- Raspberry Pi 4 (recommended) or Pi 3B+
- **Raspberry Pi Camera Module 3 Wide** (recommended)
  - Autofocus capability (motorized lens)
  - 120° diagonal field of view - ideal for greenhouse coverage
  - 11.9MP sensor with HDR support
  - Also supports: Camera Module v2, v3 standard, HQ Camera
- Adequate lighting for grow tent monitoring (LED grow lights compatible)

## Installation
1. Ensure you have Raspberry Pi OS (64-bit recommended) with camera support enabled
2. Install system dependencies:
    ```bash
    sudo apt-get update
    sudo apt-get install -y python3-picamera2 python3-paho-mqtt python3-pil python3-opencv
    ```
3. Install Python packages:
    ```bash
    pip3 install numpy opencv-python
    ```
4. Clone this repository and navigate to the project directory

## Usage

### Command Line Arguments
- `--config-file`: Path to JSON configuration file
- `--record-motion`: Enable H.264 circular buffer recording on motion detection
- `--draw-box`: Draw bounding boxes around detected motion
- `--disable-motion`: Disable motion detection entirely (streaming only mode)
- `--mqtt-broker`: MQTT broker address for event publishing (e.g., `192.168.1.100`)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Quick Start
Streaming only (no motion detection):
```bash
cd src
python3 main.py --disable-motion
```

Basic streaming with motion detection:
```bash
python3 main.py --mqtt-broker=192.168.1.100
```

With motion recording and bounding boxes:
```bash
python3 main.py --record-motion --draw-box --mqtt-broker=192.168.1.100
```

Using a configuration file:
```bash
python3 main.py --config-file=../config.json
```

### Configuration File
Example `config.json`:
```json
{
    "record_motion": true,
    "draw_box": true,
    "disable_motion": false,
    "mqtt_broker": "192.168.1.100",
    "server_port": 8000,
    "log_level": "INFO"
}
```

For streaming-only mode (best performance):
```json
{
    "disable_motion": true,
    "server_port": 8000,
    "log_level": "INFO"
}
```

### Accessing the Stream
- **Web Browser**: `http://<raspberry-pi-ip>:8000/`
- **Direct MJPEG Stream**: `http://<raspberry-pi-ip>:8000/stream.mjpg`
- **VLC Media Player**: Open Network Stream → Enter MJPEG URL

### Motion Detection Settings
Edit `src/motion_detection.py` to adjust:
- `threshold=7.0` - Motion sensitivity (lower = more sensitive)
- `log_interval=5` - Seconds between motion log messages

### Camera Module 3 Settings (Autofocus & Greenhouse Optimization)
The system is pre-configured for Camera Module 3 Wide with optimal settings for hydroponic monitoring.

Edit `src/camera_server.py` video_config controls to customize:

**Autofocus:**
- `AfMode: 2` - Continuous autofocus (keeps plants in focus as they grow)
- `AfSpeed: 0` - Normal speed (stable focusing)
- `AfRange: 0` - Normal range (10cm to infinity)
  - Change to `1` for Macro mode if camera is very close to plants

**Color & White Balance for Grow Lights:**
- `AwbMode: 1` - Auto white balance
  - Try `1` (Incandescent) if colors look purple/pink under LED lights
  - Try `3` (Fluorescent) for white/cool LED lights
- `Saturation: 1.0` - Increase to 1.2-1.3 for more vibrant plant colors

**Eliminate LED Flicker:**
- `ExposureTime: 0` - Auto exposure
  - Set to `8333` to eliminate 120Hz flicker (North America)
  - Set to `10000` to eliminate 100Hz flicker (Europe/Asia)

**Image Quality:**
- `Contrast: 1.1` - Slightly enhanced for plant detail
- `Sharpness: 1.2` - Enhanced for leaf edges and texture
- `Brightness: 0.0` - Adjust ±0.2 if too dark/bright

## System Integration
This camera system is part of a larger hydroponic monitoring ecosystem:
- **MQTT Topic**: `camera/motion` - Publishes motion detection events
- **Integration**: Works with ActuatorControl and Hydroponic_Monitor Flutter app
- **Recordings**: Motion clips saved to `~/Camera/captured_images/`

## Performance Notes
- **CPU Usage**: ~15-25% on Raspberry Pi 4 at 1080p/30fps
- **Network Bandwidth**: ~8-10 Mbps for 1080p MJPEG stream
- **Latency**: <200ms typical latency for local network viewing
- **Resolution**: Streams at 1920x1080, motion detection runs on 640x360 for efficiency

## Troubleshooting
- **No stream**: Check camera is enabled with `sudo raspi-config`
- **High CPU**: Lower resolution or frame rate in `camera_server.py`, or use `--disable-motion`
- **Motion too sensitive**: Increase threshold in `motion_detection.py`
- **MQTT not working**: Verify broker address and network connectivity
- **Blurry image**: Camera Module 3 autofocus may need time to settle (wait 2-3 seconds)
- **Purple/pink color cast**: Change `AwbMode` to `1` in camera_server.py
- **Flickering/banding**: Set `ExposureTime` to `8333` or `10000` to match AC frequency
- **Framerate is 20fps not 30fps**: This is normal - camera adjusts based on available bandwidth with 3 streams (main, lores, raw)

## Contributing
Contributions are welcome. Please fork the repository and submit a pull request with your improvements.

## License
This project is licensed under the MIT License.
