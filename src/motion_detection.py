import numpy as np
import cv2
import logging
import time

class MotionDetector:
    def __init__(self, threshold=7.0, log_interval=5):
        self.previous_frame = None
        self.threshold = threshold
        self.last_log_time = 0
        self.log_interval = log_interval  # Interval in seconds

    def detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        motion_detected = False
        if self.previous_frame is not None:
            # Check if the sizes of the current and previous frames match
            if gray.shape == self.previous_frame.shape:
                mse = np.square(np.subtract(gray, self.previous_frame)).mean()
                if mse > self.threshold:
                    motion_detected = True
                    current_time = time.time()
                    if current_time - self.last_log_time > self.log_interval:
                        logging.info("Motion detected!")
                        self.last_log_time = current_time
                    # Optionally reset previous_frame after detecting motion
                    # self.previous_frame = None
            else:
                logging.warning("Frame size mismatch detected. Skipping motion detection for this frame.")
                self.previous_frame = None  # Reset previous_frame to avoid further issues
                
        else:
            logging.debug("Previous frame is not initialized. Skipping motion detection for this frame.")
                
        self.previous_frame = gray
        return motion_detected, frame

    def draw_bounding_boxes(self, frame, gray):
        # Ensure that previous_frame is not None and sizes match
        if self.previous_frame is not None and gray.shape == self.previous_frame.shape:
            frame_delta = cv2.absdiff(self.previous_frame, gray)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) < 500:
                    continue
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        else:
            logging.warning("Cannot draw bounding boxes due to frame size mismatch or uninitialized previous_frame.")
        return frame

