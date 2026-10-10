"""
YOLOv8 Object Detection Service
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not installed. Detection disabled.")

class DetectionService:
    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cpu", conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        self.device = device
        self.model = None
        
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(model_path)
                self.model.to(device)
                print(f"✅ YOLO model loaded on {device}")
            except Exception as e:
                print(f"❌ Failed to load YOLO: {e}")
                self.model = None
        
        # COCO class names for YOLO
        self.class_names = {
            0: 'person', 2: 'car', 3: 'motorcycle', 5: 'bus', 
            7: 'truck', 1: 'bicycle', 15: 'cat', 16: 'dog',
            24: 'backpack', 26: 'handbag', 28: 'suitcase'
        }
        
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect objects in a frame
        Returns list of detections: [{class, conf, bbox: (x1,y1,x2,y2)}, ...]
        """
        if self.model is None:
            return []
        
        try:
            results = self.model(frame, conf=self.conf_threshold, verbose=False)
            detections = []
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    if cls_id in self.class_names:
                        detections.append({
                            "class": self.class_names[cls_id],
                            "confidence": conf,
                            "bbox": (int(x1), int(y1), int(x2), int(y2))
                        })
            
            return detections
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def _mock_detections(self, frame: np.ndarray) -> List[Dict]:
        """Mock detections for demo mode when YOLO unavailable"""
        h, w = frame.shape[:2]
        return [
            {"class": "person", "confidence": 0.92, "bbox": (int(w*0.3), int(h*0.4), int(w*0.4), int(h*0.8))},
            {"class": "car", "confidence": 0.88, "bbox": (int(w*0.6), int(h*0.5), int(w*0.85), int(h*0.75))},
        ]
