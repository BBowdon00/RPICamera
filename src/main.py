from config import load_configuration, parse_command_line_arguments
from utils import setup_logging
from camera_server import start_camera_server

def main():
    # Parse command-line arguments and load configuration
    args = parse_command_line_arguments()
    config = load_configuration(args)

    # Setup logging
    setup_logging(config['log_level'])

    # Start the camera server
    start_camera_server(config)

if __name__ == "__main__":
    main()

