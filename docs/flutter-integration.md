# Flutter HLS Integration Guide

## Overview
This guide shows how to integrate the H.264 HLS camera stream into your Hydroponic_Monitor Flutter app.

## Step 1: Add Dependencies

Add to `pubspec.yaml`:

```yaml
dependencies:
  video_player: ^2.8.0  # For HLS streaming
  # OR use better_player for more features:
  # better_player: ^0.0.83
```

Run:
```bash
flutter pub get
```

## Step 2: Basic HLS Player Widget

Create `lib/presentation/widgets/camera_player.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

class CameraPlayer extends StatefulWidget {
  final String streamUrl;  // e.g., "http://192.168.1.100:8000/stream.m3u8"
  
  const CameraPlayer({Key? key, required this.streamUrl}) : super(key: key);

  @override
  State<CameraPlayer> createState() => _CameraPlayerState();
}

class _CameraPlayerState extends State<CameraPlayer> {
  late VideoPlayerController _controller;
  bool _isInitialized = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  Future<void> _initializePlayer() async {
    try {
      _controller = VideoPlayerController.networkUrl(
        Uri.parse(widget.streamUrl),
        videoPlayerOptions: VideoPlayerOptions(
          mixWithOthers: true,
          allowBackgroundPlayback: false,
        ),
      );

      await _controller.initialize();
      await _controller.play();
      
      setState(() {
        _isInitialized = true;
      });

      // Auto-restart on error
      _controller.addListener(() {
        if (_controller.value.hasError) {
          setState(() {
            _error = _controller.value.errorDescription;
          });
          _reconnect();
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    }
  }

  Future<void> _reconnect() async {
    await Future.delayed(const Duration(seconds: 2));
    await _controller.dispose();
    _initializePlayer();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text('Stream Error: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _error = null;
                });
                _initializePlayer();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (!_isInitialized) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    return AspectRatio(
      aspectRatio: _controller.value.aspectRatio,
      child: Stack(
        children: [
          VideoPlayer(_controller),
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Colors.green,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Text(
                    'LIVE',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
```

## Step 3: Use in Your App

```dart
import 'package:hydroponic_monitor/presentation/widgets/camera_player.dart';

class CameraView extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Camera Feed')),
      body: CameraPlayer(
        streamUrl: 'http://192.168.1.100:8000/stream.m3u8',  // Replace with your Pi's IP
      ),
    );
  }
}
```

## Step 4 (Optional): Better Player with Controls

If you want more features (buffering indicators, quality selection, etc.), use `better_player`:

```dart
import 'package:better_player/better_player.dart';

class AdvancedCameraPlayer extends StatefulWidget {
  final String streamUrl;
  
  const AdvancedCameraPlayer({Key? key, required this.streamUrl}) : super(key: key);

  @override
  State<AdvancedCameraPlayer> createState() => _AdvancedCameraPlayerState();
}

class _AdvancedCameraPlayerState extends State<AdvancedCameraPlayer> {
  late BetterPlayerController _controller;

  @override
  void initState() {
    super.initState();
    
    BetterPlayerDataSource dataSource = BetterPlayerDataSource(
      BetterPlayerDataSourceType.network,
      widget.streamUrl,
      liveStream: true,
      bufferingConfiguration: const BetterPlayerBufferingConfiguration(
        minBufferMs: 2000,
        maxBufferMs: 10000,
        bufferForPlaybackMs: 1000,
        bufferForPlaybackAfterRebufferMs: 2000,
      ),
    );

    _controller = BetterPlayerController(
      const BetterPlayerConfiguration(
        autoPlay: true,
        looping: false,
        aspectRatio: 16 / 9,
        fit: BoxFit.contain,
        controlsConfiguration: BetterPlayerControlsConfiguration(
          enablePlayPause: false,  // Live stream doesn't need pause
          enableProgressBar: false,  // Live stream doesn't need seek
          showControlsOnInitialize: false,
        ),
      ),
      betterPlayerDataSource: dataSource,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BetterPlayer(controller: _controller);
  }
}
```

## Network Configuration

### Android
Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<manifest>
    <!-- Add this for local network access -->
    <uses-permission android:name="android.permission.INTERNET" />
    
    <application
        android:usesCleartextTraffic="true"  <!-- Required for HTTP streams -->
        ...>
    </application>
</manifest>
```

### iOS
Add to `ios/Runner/Info.plist`:

```xml
<dict>
    <!-- Add this for local network access -->
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsLocalNetworking</key>
        <true/>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
```

## Configuration Management

Store camera URL in your app configuration:

```dart
// lib/core/config/app_config.dart
class AppConfig {
  static const String cameraStreamUrl = 'http://192.168.1.100:8000/stream.m3u8';
  
  // Or load from environment/settings
  static String getCameraUrl() {
    // Could load from SharedPreferences, remote config, etc.
    return 'http://192.168.1.100:8000/stream.m3u8';
  }
}
```

## Troubleshooting

### "Failed to load video"
- Check that Raspberry Pi is running: `sudo systemctl status camera.service`
- Verify URL is accessible: Open `http://PI_IP:8000` in mobile browser
- Ensure phone is on same network as Raspberry Pi

### High latency
- HLS typically has 2-6 seconds latency (normal)
- Adjust segment duration in `camera_server.py` HLSOutput (smaller = lower latency but more overhead)

### Buffering issues
- Increase `bufferForPlaybackMs` in BetterPlayer config
- Check network signal strength
- Consider reducing video quality in camera_server.py if bandwidth is limited

## Integration with Existing Architecture

If using your existing architecture pattern:

```dart
// lib/data/datasources/camera_remote_datasource.dart
abstract class CameraRemoteDataSource {
  String getStreamUrl();
}

class CameraRemoteDataSourceImpl implements CameraRemoteDataSource {
  final String baseUrl;
  
  CameraRemoteDataSourceImpl({required this.baseUrl});
  
  @override
  String getStreamUrl() => '$baseUrl/stream.m3u8';
}

// lib/domain/usecases/get_camera_stream.dart
class GetCameraStream {
  final CameraRepository repository;
  
  GetCameraStream(this.repository);
  
  String call() => repository.getStreamUrl();
}
```

## Performance Tips

1. **Dispose properly**: Always dispose controllers in `dispose()` to avoid memory leaks
2. **Handle background**: Stop stream when app goes to background to save bandwidth
3. **Error handling**: Implement auto-reconnect for network interruptions
4. **Loading states**: Show loading indicators during initialization

## Next Steps

- Implement full-screen mode toggle
- Add picture-in-picture support for Android
- Integrate with your existing plant monitoring UI
- Add recording capability (save video clips)
