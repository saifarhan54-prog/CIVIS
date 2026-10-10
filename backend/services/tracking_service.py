"""
Object Tracking Service using ByteTrack-style logic
"""
import numpy as np
from typing import List, Dict
from collections import defaultdict
from scipy.spatial.distance import cdist

class Track:
    def __init__(self, track_id: int, bbox: tuple, class_name: str, confidence: float = 0.0):
        self.id = track_id
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.class_name = class_name
        self.positions = []  # List of centroids over time
        self.age = 0
        self.hits = 0
        self.time_since_update = 0
        self.confidence = confidence
        
    def update(self, bbox: tuple, confidence: float = 0.0):
        self.bbox = bbox
        centroid = self._get_centroid(bbox)
        self.positions.append(centroid)
        self.hits += 1
        self.time_since_update = 0
        self.confidence = confidence
        
    def predict(self):
        self.age += 1
        self.time_since_update += 1
        
    def _get_centroid(self, bbox: tuple) -> tuple:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def get_velocity(self) -> tuple:
        """Estimate velocity from recent positions"""
        if len(self.positions) < 2:
            return (0, 0)
        recent = self.positions[-5:]  # Last 5 positions
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        return (dx, dy)

class TrackingService:
    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: List[Track] = []
        self.next_id = 1
        self.id_prefix = {}  # class -> count mapping for IDs like PERSON_12
        
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracks with new detections
        Returns list of tracked objects with IDs
        """
        # Predict existing tracks
        for track in self.tracks:
            track.predict()
        
        # Match detections to tracks
        if len(detections) > 0 and len(self.tracks) > 0:
            matches, unmatched_dets, unmatched_tracks = self._match(detections)
            
            # Update matched tracks
            for det_idx, track_idx in matches:
                self.tracks[track_idx].update(detections[det_idx]["bbox"], detections[det_idx].get("confidence", 0.0))
            
            # Create new tracks for unmatched detections
            for det_idx in unmatched_dets:
                self._create_track(detections[det_idx])
            
        
        elif len(detections) > 0:
            # No existing tracks, create new ones
            for det in detections:
                self._create_track(det)
        
        # Expire stale tracks even on empty-detection frames. Only expose tracks
        # observed in this frame so old boxes cannot create false incidents.
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # Return active tracks
        result = []
        for track in self.tracks:
            if track.time_since_update == 0 and (track.hits >= self.min_hits or track.age <= self.min_hits):
                result.append({
                    "track_id": track.id,
                    "class": track.class_name,
                    "bbox": track.bbox,
                    "confidence": track.confidence,
                    "velocity": track.get_velocity(),
                    "trajectory": track.positions[-20:]  # Last 20 positions
                })
        
        return result
    
    def _create_track(self, detection: Dict):
        """Create a new track"""
        class_name = detection["class"]
        
        # Generate semantic ID like "PERSON_12"
        if class_name not in self.id_prefix:
            self.id_prefix[class_name] = 0
        self.id_prefix[class_name] += 1
        
        track_id = f"{class_name.upper()}_{self.id_prefix[class_name]}"
        
        track = Track(track_id, detection["bbox"], class_name, detection.get("confidence", 0.0))
        self.tracks.append(track)
    
    def _match(self, detections: List[Dict]) -> tuple:
        """Match detections to tracks using IoU"""
        if len(self.tracks) == 0:
            return [], list(range(len(detections))), []
        
        # Compute IoU matrix
        iou_matrix = np.zeros((len(detections), len(self.tracks)))
        for d, det in enumerate(detections):
            for t, track in enumerate(self.tracks):
                if det["class"] == track.class_name:
                    overlap = self._iou(det["bbox"], track.bbox)
                    # Detector boxes jitter and move between sampled frames. When
                    # IoU is weak, use a bounded center-distance fallback for the
                    # same class so walking objects retain their IDs.
                    if overlap <= self.iou_threshold:
                        dx1, dy1, dx2, dy2 = det["bbox"]
                        tx1, ty1, tx2, ty2 = track.bbox
                        distance = np.hypot((dx1 + dx2 - tx1 - tx2) / 2,
                                            (dy1 + dy2 - ty1 - ty2) / 2)
                        width = max(dx2 - dx1, tx2 - tx1)
                        height = max(dy2 - dy1, ty2 - ty1)
                        radius = min(160.0, max(50.0, 0.75 * np.hypot(width, height)))
                        if distance < radius:
                            proximity_score = self.iou_threshold + 0.01 + 0.09 * (1 - distance / radius)
                            overlap = max(overlap, proximity_score)
                    iou_matrix[d, t] = overlap
        
        # Simple greedy matching
        matches = []
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(range(len(self.tracks)))
        
        while iou_matrix.size > 0 and iou_matrix.max() > self.iou_threshold:
            d, t = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
            matches.append((d, t))
            unmatched_dets.remove(d)
            unmatched_tracks.remove(t)
            iou_matrix[d, :] = 0
            iou_matrix[:, t] = 0
        
        return matches, unmatched_dets, unmatched_tracks
    
    @staticmethod
    def _iou(bbox1: tuple, bbox2: tuple) -> float:
        """Calculate Intersection over Union"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
