#!/bin/bash
# Quick start script for HLS streaming

cd "$(dirname "$0")/src"

echo "Starting Hydroponic Camera System with HLS streaming..."
echo "Access stream at: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 main.py --stream-format=hls --disable-motion
