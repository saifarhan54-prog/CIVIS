"""
Automatic License Plate Recognition Service
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

class ALPRService:
    def __init__(self, languages: List[str] = ["en"]):
        self.languages = languages
        self.reader = None
        self.model_dir = Path(__file__).parent.parent / "models" / "easyocr"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.user_network_dir = self.model_dir / "user_network"
        self.user_network_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import easyocr
            self.reader = easyocr.Reader(languages, gpu=False, model_storage_directory=str(self.model_dir), user_network_directory=str(self.user_network_dir), download_enabled=True)
            print('ALPR ready with EasyOCR')
        except Exception as exc:
            print(f"ALPR unavailable: {exc}")
    
    def detect_plates(self, frame: np.ndarray, vehicle_bboxes: List[tuple]) -> List[Dict]:
        """
        Detect and read license plates from vehicle regions
        Returns list of {license_plate, confidence, vehicle_bbox}
        """
        if self.reader is None:
            return []
        
        results = []
        
        for bbox in vehicle_bboxes:
            x1, y1, x2, y2 = bbox
            
            # Expand bbox slightly to capture license plate
            h, w = frame.shape[:2]
            y1_exp = max(0, int(y1 - (y2 - y1) * 0.1))
            y2_exp = min(h, int(y2 + (y2 - y1) * 0.1))
            x1_exp = max(0, int(x1 - (x2 - x1) * 0.1))
            x2_exp = min(w, int(x2 + (x2 - x1) * 0.1))
            
            vehicle_crop = frame[y1_exp:y2_exp, x1_exp:x2_exp]
            
            if vehicle_crop.size == 0:
                continue
            
            # Read text from vehicle region
            try:
                detections = self.reader.readtext(vehicle_crop)
                
                for (bbox_ocr, text, conf) in detections:
                    # Filter for license plate patterns
                    if self._is_likely_plate(text) and conf > 0.6:
                        results.append({
                            "license_plate": text.upper().replace(" ", ""),
                            "confidence": conf,
                            "vehicle_bbox": bbox
                        })
                        break  # Take first valid plate per vehicle
            except Exception as e:
                print(f"ALPR error: {e}")
                continue
        
        return results
    
    def _is_likely_plate(self, text: str) -> bool:
        """
        Check if text matches license plate patterns
        Adjust regex for your region
        """
        import re
        
        # Remove spaces
        text = text.replace(" ", "").upper()
        
        # Basic pattern: mix of letters and numbers, length 5-10
        if not re.match(r'^[A-Z0-9]{5,10}$', text):
            return False
        
        # Should have at least one letter and one number
        has_letter = any(c.isalpha() for c in text)
        has_number = any(c.isdigit() for c in text)
        
        return has_letter and has_number
    
    def estimate_speed(self, trajectory: List[tuple], fps: float, 
                      pixels_per_meter: float = 10.0) -> float:
        """
        Estimate vehicle speed from trajectory
        trajectory: list of (x, y, timestamp) positions
        Returns speed in km/h
        """
        if len(trajectory) < 2:
            return 0.0
        
        # Calculate distance traveled
        total_distance = 0
        for i in range(1, len(trajectory)):
            x1, y1, t1 = trajectory[i-1]
            x2, y2, t2 = trajectory[i]
            
            pixel_distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_distance += pixel_distance / pixels_per_meter  # Convert to meters
        
        # Calculate time elapsed
        time_elapsed = trajectory[-1][2] - trajectory[0][2]  # seconds
        
        if time_elapsed == 0:
            return 0.0
        
        # Speed in m/s, convert to km/h
        speed_ms = total_distance / time_elapsed
        speed_kmh = speed_ms * 3.6
        
        return speed_kmh
