"""Video-time behavioral rules for loitering, crowds and unattended bags."""
from collections import defaultdict
from typing import Dict, List

import numpy as np


class BehavioralAnalyzer:
    # Deliberately exposed as class settings so deployments can tune rules.
    LOITERING_SECONDS = 30
    ABANDONED_SECONDS = 60
    STATIONARY_RADIUS_PX = 24

    def __init__(self):
        self.object_positions = defaultdict(list)
        self.stationary_objects = {}

    def reset(self):
        self.object_positions.clear()
        self.stationary_objects.clear()

    def analyze(self, tracked_objects: List[Dict], video_time: float = 0.0,
                frame_size=None) -> List[Dict]:
        """Analyze one sampled frame; all durations use source-video seconds."""
        for obj in tracked_objects:
            track_id = obj["track_id"]
            bbox = obj["bbox"]
            center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            history = self.object_positions[track_id]
            history.append((center[0], center[1], video_time))
            self.object_positions[track_id] = [p for p in history if video_time - p[2] <= 300]

        events = []
        events.extend(self._detect_loitering(tracked_objects, video_time))
        events.extend(self._detect_crowds(tracked_objects, frame_size))
        events.extend(self._detect_abandoned(tracked_objects, video_time))
        return events

    def _is_stationary(self, track_id):
        positions = self.object_positions.get(track_id, [])
        if len(positions) < 8:
            return False
        recent = positions[-min(30, len(positions)):]
        coords = np.asarray([(p[0], p[1]) for p in recent])
        return float(np.linalg.norm(coords[-1] - coords[0])) <= self.STATIONARY_RADIUS_PX

    def _detect_loitering(self, tracked_objects, video_time):
        events = []
        visible_people = {o["track_id"] for o in tracked_objects if o["class"] == "person"}
        for obj in tracked_objects:
            if obj["class"] != "person":
                continue
            track_id = obj["track_id"]
            if self._is_stationary(track_id):
                start = self.stationary_objects.setdefault(track_id, self.object_positions[track_id][0][2])
                duration = max(0.0, video_time - start)
                if duration >= self.LOITERING_SECONDS:
                    events.append({
                        "type": "LOITERING", "severity": "MEDIUM",
                        "object_ids": [track_id], "duration": round(duration, 1),
                        "location": obj["bbox"],
                        "reason": f"{track_id} remained in a small area for {int(duration)}s of video time",
                    })
            else:
                self.stationary_objects.pop(track_id, None)
        for track_id in list(self.stationary_objects):
            if track_id not in visible_people:
                self.stationary_objects.pop(track_id, None)
        return events

    def _detect_crowds(self, tracked_objects, frame_size=None, threshold=10):
        people = [o for o in tracked_objects if o["class"] == "person"]
        if len(people) <= threshold:
            return []
        centers = np.asarray([((o["bbox"][0] + o["bbox"][2]) / 2,
                               (o["bbox"][1] + o["bbox"][3]) / 2) for o in people])
        # Use spread relative to image size, avoiding resolution-dependent pixel thresholds.
        scale = min(frame_size) if frame_size else 720
        spread = float(np.linalg.norm(np.std(centers, axis=0))) / max(scale, 1)
        if spread >= 0.28:
            return []
        ids = [o["track_id"] for o in people]
        return [{"type": "CROWD_FORMATION", "severity": "MEDIUM", "object_ids": ids,
                 "count": len(people), "reason": f"Cluster of {len(people)} people detected (threshold: {threshold})"}]

    def _detect_abandoned(self, tracked_objects, video_time):
        people = [o for o in tracked_objects if o["class"] == "person"]
        bag_classes = {"backpack", "handbag", "suitcase"}
        events = []
        for obj in tracked_objects:
            if obj["class"] not in bag_classes:
                continue
            track_id = obj["track_id"]
            if not self._is_stationary(track_id):
                continue
            positions = self.object_positions[track_id]
            duration = video_time - positions[0][2]
            if duration < self.ABANDONED_SECONDS:
                continue
            x1, y1, x2, y2 = obj["bbox"]
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            nearest = min((np.linalg.norm(np.asarray(center) - np.asarray(((p["bbox"][0] + p["bbox"][2]) / 2,
                                                                (p["bbox"][1] + p["bbox"][3]) / 2)))
                           for p in people), default=float("inf"))
            if nearest > 100:
                events.append({"type": "ABANDONED_OBJECT", "severity": "HIGH",
                               "object_ids": [track_id], "duration": round(duration, 1),
                               "location": obj["bbox"],
                               "reason": f"{obj['class']} {track_id} stationary without a nearby person for {int(duration)}s"})
        return events
