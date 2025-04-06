import cv2
import uuid

class TrackerManager:
    def __init__(self, tracker_type="CSRT"):
        self.tracker_type = tracker_type
        self.trackers = {}  # id -> tracker
        self.bboxes = {}    # id -> last bbox (x, y, w, h)

    def _create_tracker(self):
        if self.tracker_type == "CSRT":
            return cv2.TrackerCSRT_create()
        elif self.tracker_type == "KCF":
            return cv2.TrackerKCF_create()
        elif self.tracker_type == "MOSSE":
            return cv2.TrackerMOSSE_create()
        else:
            raise ValueError(f"Unsupported tracker type: {self.tracker_type}")

    def add(self, frame, bbox):
        """Add a new tracker for the given bounding box."""
        tracker = self._create_tracker()
        tracker.init(frame, bbox)
        obj_id = str(uuid.uuid4())[:8]
        self.trackers[obj_id] = tracker
        self.bboxes[obj_id] = bbox

    def update_all(self, frame):
        """Update all trackers and prune failed ones."""
        new_bboxes = {}
        to_remove = []

        for obj_id, tracker in self.trackers.items():
            success, bbox = tracker.update(frame)
            if success:
                new_bboxes[obj_id] = bbox
            else:
                to_remove.append(obj_id)

        for obj_id in to_remove:
            del self.trackers[obj_id]
            del self.bboxes[obj_id]

        self.bboxes = new_bboxes
        return new_bboxes

    def reset(self):
        """Remove all trackers."""
        self.trackers.clear()
        self.bboxes.clear()

