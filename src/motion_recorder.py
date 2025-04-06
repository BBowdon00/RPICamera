import os
import time
import logging

class MotionRecorder:
    def __init__(self, encoder_output, save_dir, timeout=5, buffer_seconds=10):
        """
        Initializes the motion recorder.

        :param encoder_output: A CircularOutput instance from picamera2
        :param save_dir: Directory where clips should be saved
        :param timeout: Time (in seconds) after last motion to stop and save
        :param buffer_seconds: How much footage to buffer before motion
        """
        self.output = encoder_output
        self.save_dir = save_dir
        self.timeout = timeout
        self.buffer_seconds = buffer_seconds
        self.recording = False
        self.last_motion_time = 0

        # Ensure directory exists
        os.makedirs(self.save_dir, exist_ok=True)

    def update(self, motion_detected, current_time=None):
        """
        Called every frame to update the recording state based on motion.

        :param motion_detected: Whether motion was detected in this frame
        :param current_time: Timestamp in seconds (default: time.time())
        """
        current_time = current_time or time.time()

        if motion_detected:
            self.last_motion_time = current_time
            if not self.recording:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = os.path.join(self.save_dir, f"motion_{timestamp}.h264")
                self.output.fileoutput = filename
                self.output.start()
                self.recording = True
                logging.info(f"Started recording to: {filename}")

        if self.recording and (current_time - self.last_motion_time > self.timeout):
            self.output.stop()
            logging.info("Stopped recording due to inactivity.")
            self.recording = False

