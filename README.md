
# Camera Streaming and Motion Detection System

## Overview
This project provides a motion detection and streaming system using the Raspberry Pi's camera and the Picamera2 library. The system supports MJPEG streaming, motion detection with optional bounding boxes, and event publishing via MQTT.

## Features
- **Real-time MJPEG streaming** via HTTP.
- **Motion detection** with adjustable sensitivity.
- **MQTT integration** for event notifications.
- **Timestamp overlay** on streaming video.
- **Configurable** via command-line arguments and configuration file.

## Installation
1. Ensure you have a Raspberry Pi with a camera module.
2. Install the required dependencies:
    ```bash
    sudo apt-get update
    sudo apt-get install -y python3-picamera2 python3-paho-mqtt python3-pil
    pip install numpy opencv-python
    ```
3. Clone this repository and navigate to the project directory.

## Usage
### Command Line Arguments
- `--config-file`: Path to the JSON configuration file.
- `--circular-buffer`: Enable circular buffer recording on motion detection.
- `--bounding-box`: Draw bounding box around detected motion.
- `--mqtt-broker`: MQTT broker address for event publishing.
- `--log-level`: Set the logging level (default: INFO).

### Running the Application
To start the application, run the following command:
```bash
python3 main.py --config-file=config.json --mqtt-broker=broker_address --log-level=DEBUG
```

### Configuration File
You can specify the settings in a JSON configuration file. An example configuration:
```json
{
    "circular_buffer": true,
    "bounding_box": true,
    "mqtt_broker": "192.168.1.100",
    "log_level": "INFO"
}
```

## Testing
Since the application heavily relies on specific hardware (Raspberry Pi with camera), testing should be conducted on the target device. Ensure that the `picamera2` library is correctly installed and configured.

## Contributing
Contributions are welcome. Please fork the repository and submit a pull request with your improvements.

## License
This project is licensed under the MIT License.
