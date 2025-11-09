"""
HLS (HTTP Live Streaming) output handler for H.264 video streaming.
Generates .m3u8 playlist and .ts segment files for adaptive bitrate streaming.
"""
import os
import io
import time
import logging
from threading import Lock
from collections import deque


class HLSOutput:
    """Manages HLS playlist and segment files for H.264 streaming."""
    
    def __init__(self, output_dir="/tmp/hls", segment_time=2, playlist_size=6):
        """
        Initialize HLS output handler.
        
        Args:
            output_dir: Directory to store HLS files
            segment_time: Duration of each .ts segment in seconds
            playlist_size: Number of segments to keep in playlist
        """
        self.output_dir = output_dir
        self.segment_time = segment_time
        self.playlist_size = playlist_size
        self.segment_index = 0
        self.segments = deque(maxlen=playlist_size)
        self.lock = Lock()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean up old segments
        self._cleanup_old_files()
        
        logging.info(f"HLS output initialized: {output_dir}")
    
    def _cleanup_old_files(self):
        """Remove old HLS files from previous runs."""
        try:
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.ts') or filename.endswith('.m3u8'):
                    os.remove(os.path.join(self.output_dir, filename))
            logging.info("Cleaned up old HLS files")
        except Exception as e:
            logging.warning(f"Failed to cleanup old HLS files: {e}")
    
    def get_segment_filename(self, index):
        """Generate filename for a segment."""
        return f"segment_{index:06d}.ts"
    
    def add_segment(self, index, duration):
        """
        Add a new segment to the playlist.
        
        Args:
            index: Segment index number
            duration: Duration of the segment in seconds
        """
        with self.lock:
            filename = self.get_segment_filename(index)
            self.segments.append({
                'index': index,
                'filename': filename,
                'duration': duration
            })
            
            # Remove old segment files that are no longer in playlist
            if len(self.segments) == self.playlist_size:
                old_index = index - self.playlist_size
                if old_index >= 0:
                    old_file = os.path.join(self.output_dir, self.get_segment_filename(old_index))
                    try:
                        if os.path.exists(old_file):
                            os.remove(old_file)
                    except Exception as e:
                        logging.warning(f"Failed to remove old segment {old_file}: {e}")
    
    def generate_playlist(self):
        """
        Generate M3U8 playlist content.
        
        Returns:
            str: M3U8 playlist content
        """
        with self.lock:
            if not self.segments:
                return None
            
            # Get the maximum duration for #EXTINF
            max_duration = max(seg['duration'] for seg in self.segments)
            
            # Generate M3U8 content
            playlist = [
                "#EXTM3U",
                "#EXT-X-VERSION:3",
                f"#EXT-X-TARGETDURATION:{int(max_duration) + 1}",
                "#EXT-X-MEDIA-SEQUENCE:{}".format(self.segments[0]['index']),
            ]
            
            for seg in self.segments:
                playlist.append(f"#EXTINF:{seg['duration']:.3f},")
                playlist.append(seg['filename'])
            
            return "\n".join(playlist) + "\n"
    
    def get_playlist_path(self):
        """Get the path to the M3U8 playlist file."""
        return os.path.join(self.output_dir, "stream.m3u8")
    
    def get_segment_path(self, filename):
        """Get the full path to a segment file."""
        return os.path.join(self.output_dir, filename)
    
    def write_playlist(self):
        """Write the M3U8 playlist to disk."""
        playlist_content = self.generate_playlist()
        if playlist_content:
            try:
                playlist_path = self.get_playlist_path()
                with open(playlist_path, 'w') as f:
                    f.write(playlist_content)
            except Exception as e:
                logging.error(f"Failed to write playlist: {e}")


class HLSSegmentOutput(io.BufferedIOBase):
    """
    File output for HLS segments that interfaces with picamera2.
    Writes segments and manages the HLS playlist.
    Inherits from io.BufferedIOBase to work with FileOutput.
    """
    
    def __init__(self, hls_manager, segment_duration=2):
        """
        Initialize HLS segment output.
        
        Args:
            hls_manager: HLSOutput instance to manage segments
            segment_duration: Target duration for each segment in seconds
        """
        self.hls_manager = hls_manager
        self.segment_duration = segment_duration
        self.current_segment_index = 0
        self.current_segment_file = None
        self.segment_start_time = None
        self.bytes_written = 0
        
    def _start_new_segment(self):
        """Start a new segment file."""
        # Close previous segment
        if self.current_segment_file:
            self.current_segment_file.close()
            
            # Calculate actual duration
            duration = time.time() - self.segment_start_time
            
            # Add segment to manager
            self.hls_manager.add_segment(self.current_segment_index - 1, duration)
            self.hls_manager.write_playlist()
            
            logging.debug(f"Completed segment {self.current_segment_index - 1}, duration: {duration:.2f}s")
        
        # Open new segment file
        filename = self.hls_manager.get_segment_filename(self.current_segment_index)
        filepath = self.hls_manager.get_segment_path(filename)
        self.current_segment_file = open(filepath, 'wb')
        self.segment_start_time = time.time()
        self.bytes_written = 0
        
        self.current_segment_index += 1
    
    def write(self, buf):
        """
        Write video data to current segment.
        
        Args:
            buf: Video data buffer to write
        """
        # Start first segment if needed
        if self.current_segment_file is None:
            self._start_new_segment()
        
        # Write data to current segment
        self.current_segment_file.write(buf)
        self.current_segment_file.flush()
        self.bytes_written += len(buf)
        
        # Check if it's time for a new segment
        elapsed = time.time() - self.segment_start_time
        if elapsed >= self.segment_duration:
            self._start_new_segment()
    
    def close(self):
        """Close the output and finalize playlist."""
        if self.current_segment_file:
            self.current_segment_file.close()
            
            # Add final segment
            duration = time.time() - self.segment_start_time
            self.hls_manager.add_segment(self.current_segment_index - 1, duration)
            self.hls_manager.write_playlist()
            
            logging.info("HLS output closed")
