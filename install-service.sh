#!/bin/bash
# Installation script for camera systemd service

echo "Installing Hydroponic Camera Service..."

# Check if running on Raspberry Pi
if [ ! -f /etc/rpi-issue ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the actual username and camera directory
CAMERA_USER=$(whoami)
CAMERA_DIR=$(pwd)

echo "User: $CAMERA_USER"
echo "Camera directory: $CAMERA_DIR"

# Check for virtual environment
VENV_PYTHON=""
if [ -f "$CAMERA_DIR/src/camera_env/bin/python" ]; then
    VENV_PYTHON="$CAMERA_DIR/src/camera_env/bin/python"
    echo "Found virtual environment: camera_env"
elif [ -f "$CAMERA_DIR/camera_env/bin/python" ]; then
    VENV_PYTHON="$CAMERA_DIR/camera_env/bin/python"
    echo "Found virtual environment: camera_env"
else
    echo "Warning: Virtual environment not found at $CAMERA_DIR/src/camera_env"
    echo "Falling back to system Python"
    VENV_PYTHON="/usr/bin/python3"
fi

echo "Python interpreter: $VENV_PYTHON"

# Create the service file with actual paths
SERVICE_FILE="/tmp/camera.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Hydroponic Camera Streaming Service
After=network.target

[Service]
Type=simple
User=$CAMERA_USER
WorkingDirectory=$CAMERA_DIR/src
ExecStart=$VENV_PYTHON $CAMERA_DIR/src/main.py --stream-format=hls --disable-motion --low-latency
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Copy service file to systemd
echo "Installing service file..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/camera.service

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service..."
sudo systemctl enable camera.service

# Start service now
echo "Starting service..."
sudo systemctl start camera.service

# Show status
echo ""
echo "Service installed and started!"
echo ""
echo "Useful commands:"
echo "  Check status:        sudo systemctl status camera"
echo "  View logs:          sudo journalctl -u camera -f"
echo "  Stop service:       sudo systemctl stop camera"
echo "  Start service:      sudo systemctl start camera"
echo "  Restart service:    sudo systemctl restart camera"
echo "  Disable on boot:    sudo systemctl disable camera"
echo ""

# Check if service is running
sleep 2
if systemctl is-active --quiet camera.service; then
    echo "✓ Camera service is running!"
    IP_ADDR=$(hostname -I | awk '{print $1}')
    echo "✓ Stream available at: http://$IP_ADDR:8000"
else
    echo "✗ Service failed to start. Check logs with: sudo journalctl -u camera -f"
fi
