"""
Face Recognition Service with Anti-Spoofing
"""
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Optional

# Local face detection only. This service does not identify people.
class FaceRecognitionService:
    def __init__(self, enable_antispoofing: bool = True):
        self.enable_antispoofing = enable_antispoofing
        self.known_faces = {}  # person_id -> encoding
        self.spoofing_detector = None
        model_path = Path(__file__).parent.parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
        self.face_detector = None
        if model_path.is_file() and hasattr(cv2, "FaceDetectorYN_create"):
            try:
                self.face_detector = cv2.FaceDetectorYN_create(str(model_path), "", (320, 320), 0.6, 0.3, 5000)
            except cv2.error as exc:
                print(f"Face detection unavailable: {exc}")
        
    
    @property
    def available(self) -> bool:
        return self.face_detector is not None

    def detect_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces in frame
        Returns list of face detections with bounding boxes
        """
        if not self.available or frame is None or frame.size == 0:
            return []
        height, width = frame.shape[:2]
        resized = cv2.resize(frame, (320, 320))
        _, faces = self.face_detector.detect(resized)
        if faces is None:
            return []
        scale_x, scale_y = width / 320, height / 320
        return [{
            "bbox": (int(x * scale_x), int(y * scale_y), int((x + w) * scale_x), int((y + h) * scale_y)),
            "confidence": float(face[-1]),
        } for face in faces for x, y, w, h in [face[:4]]]
    
    def recognize_face(self, frame: np.ndarray, face_bbox: tuple) -> Optional[Dict]:
        """
        Recognize a face and check for spoofing
        Returns {person_id, name, confidence, is_spoof}
        """
        if self.enable_antispoofing:
            is_spoof = self._check_spoofing(frame, face_bbox)
            if is_spoof:
                return {
                    "person_id": "UNKNOWN",
                    "name": "Unknown",
                    "confidence": 0.0,
                    "is_spoof": True,
                    "liveness_score": 0.2
                }
        
        raise NotImplementedError("Identity matching is not implemented; this service only returns face bounding boxes.")
    
    def _check_spoofing(self, frame: np.ndarray, face_bbox: tuple) -> bool:
        """
        Check if face is real or spoofed (photo/screen)
        Uses Silent-Face-Anti-Spoofing or similar
        """
        # In production:
        # from silent_face_anti_spoofing import AntiSpoofing
        # is_real = anti_spoofing_model.predict(face_crop)
        
        raise NotImplementedError("Anti-spoofing is not implemented; no liveness result is available.")
    
    def add_authorized_face(self, person_id: str, name: str, encoding: np.ndarray):
        """Add a face to the authorized database"""
        self.known_faces[person_id] = {
            "name": name,
            "encoding": encoding
        }
