import argparse
import json
import logging
from pathlib import Path

def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description="Picamera2 Motion Detection with MJPEG Streaming")
    parser.add_argument("--config-file", type=str, help="Path to configuration file", required=False)
    parser.add_argument("--record-motion", action="store_true", help="Enable circular buffer recording on motion detection")
    parser.add_argument("--bounding-box", action="store_true", help="Draw bounding boxes around detected motion")
    parser.add_argument("--mqtt-broker", type=str, help="MQTT broker address to publish motion detection events")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    return parser.parse_args()

def load_configuration(args):
    config = vars(args)  # Start with the command-line arguments as the base configuration
    if args.config_file:
        config_path = Path(args.config_file)
        if config_path.is_file():
            with open(config_path, 'r') as file:
                file_config = json.load(file)
                config.update(file_config)  # Merge the configuration file settings

    # Validate the log level
    log_level = config.get('log_level', 'INFO').upper()
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_log_levels:
        logging.warning(f"Invalid log level: {log_level}. Defaulting to INFO.")
        config['log_level'] = "INFO"

    return config


