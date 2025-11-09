# H.264 HLS Streaming - Implementation Summary

## What Was Done

Implemented H.264 HLS (HTTP Live Streaming) as the default streaming method for the RPICamera system, providing significantly better video quality than MJPEG at lower bandwidth.

## Changes Made

### New Files Created

1. **`src/hls_output.py`** - Core HLS implementation
   - `HLSOutput` class: Manages playlist and segment files
   - `HLSSegmentOutput` class: Interfaces with picamera2 to write H.264 segments
   - Automatic cleanup of old segments
   - 2-second segment duration with 6-segment playlist (12 seconds total buffer)

2. **`docs/flutter-integration.md`** - Complete Flutter integration guide
   - Basic video_player implementation
   - Advanced better_player example with controls
   - Network configuration for Android/iOS
   - Error handling and reconnection logic
   - Performance optimization tips

### Modified Files

1. **`src/camera_server.py`**
   - Added HLS streaming support with dual-mode operation
   - Default mode: HLS (H.264 @ 5 Mbps)
   - Legacy mode: MJPEG (@ 30 Mbps)
   - Motion detection still works in HLS mode using separate low-res MJPEG encoder
   - Automatic encoder management based on selected mode

2. **`src/streaming.py`**
   - Added `HLS_PAGE` with hls.js video player
   - Updated `StreamingHandler` to serve:
     - `/stream.m3u8` - HLS playlist
     - `/segment_*.ts` - Video segments
     - `/stream.mjpg` - Legacy MJPEG stream
   - Status indicator (Loading/Live/Error) on video player
   - Fullscreen button for both HLS and MJPEG modes

3. **`src/config.py`**
   - Added `--stream-format` argument
   - Choices: `hls` (default) or `mjpeg`
   - Updated help text to reflect H.264 support

4. **`README.md`**
   - Updated feature list to highlight HLS as default
   - Added streaming format comparison
   - Updated quick start examples
   - Added performance comparison between HLS and MJPEG
   - Linked to Flutter integration guide

5. **`.github/copilot-instructions.md`**
   - Updated architecture section with HLS streaming details
   - Added notes about dual-encoder setup for motion detection

## How to Use

### Start with HLS (Default - Recommended)
```bash
cd src
python3 main.py --stream-format=hls --disable-motion
```

Access in browser: `http://PI_IP:8000`

### Switch to MJPEG (Legacy)
```bash
python3 main.py --stream-format=mjpeg --disable-motion
```

### Flutter Integration
See `docs/flutter-integration.md` for complete guide.

Quick example:
```dart
import 'package:video_player/video_player.dart';

VideoPlayerController.networkUrl(
  Uri.parse('http://192.168.1.100:8000/stream.m3u8')
);
```

## Quality Comparison

### HLS (H.264) - **RECOMMENDED**
- ✅ 5 Mbps bitrate for excellent 1080p quality
- ✅ 5-10x more efficient than MJPEG
- ✅ Works everywhere (browsers, mobile, Flutter, VLC)
- ✅ Adaptive streaming ready (future enhancement)
- ⚠️ 2-4 second latency (acceptable for monitoring)

### MJPEG - Legacy
- ✅ Near real-time (<200ms latency)
- ❌ 30 Mbps needed for acceptable quality
- ❌ High bandwidth consumption
- ❌ Each frame compressed independently (inefficient)
- ⚠️ Limited mobile app support

## Technical Details

### HLS Segmentation
- **Segment Duration**: 2 seconds
- **Playlist Size**: 6 segments (12 seconds buffer)
- **Storage**: `/tmp/hls/` (temporary, auto-cleanup)
- **Format**: MPEG-TS containers with H.264 video

### Dual-Encoder Architecture (HLS Mode)
When using HLS with motion detection:
1. **Main encoder** (H.264): 1080p @ 5 Mbps → HLS segments → Web viewers
2. **Motion encoder** (MJPEG): 360p low-res → Motion detector → MQTT events

This allows high-quality streaming without compromising motion detection performance.

### Browser Compatibility
- **Chrome/Edge**: hls.js (included in page)
- **Firefox**: hls.js (included in page)
- **Safari/iOS**: Native HLS support
- **Android Chrome**: Native HLS support

## Testing Checklist

- [ ] Start camera with HLS mode
- [ ] Open `http://PI_IP:8000` in browser
- [ ] Verify video plays smoothly
- [ ] Check fullscreen button works
- [ ] Verify "LIVE" indicator shows green
- [ ] Test motion detection (if enabled)
- [ ] Test Flutter integration (if applicable)
- [ ] Compare quality to MJPEG mode
- [ ] Monitor CPU usage (~20-30% expected)
- [ ] Check network bandwidth (~5 Mbps expected)

## Future Enhancements

Potential improvements for future versions:

1. **Adaptive Bitrate**: Multiple quality levels, automatic switching
2. **Lower Latency**: Reduce segment duration to 1 second
3. **Audio Support**: Add microphone input to segments
4. **HTTPS Support**: Secure streaming with Let's Encrypt
5. **Authentication**: Add basic auth or token-based access
6. **Recording Integration**: Direct HLS segments to motion recorder
7. **Multi-camera**: Serve multiple camera streams from one server

## Rollback

If you need to revert to MJPEG-only:

1. Use `--stream-format=mjpeg` flag
2. Or set `"stream_format": "mjpeg"` in config.json

No code changes needed - both modes are fully supported.

## Support

- **HLS Issues**: Check browser console for hls.js errors
- **Network Issues**: Verify Pi and client on same network
- **Quality Issues**: Adjust bitrate in `camera_server.py` line 94
- **Flutter Issues**: See troubleshooting in `docs/flutter-integration.md`
