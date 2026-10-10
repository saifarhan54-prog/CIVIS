"""Rule-based incident and session-risk scoring for detected objects."""
from typing import Dict, List, Tuple
import numpy as np


class RiskEngine:
    SEVERITY_POINTS = {"LOW": 15, "MEDIUM": 35, "HIGH": 60, "CRITICAL": 85}
    EVENT_FACTORS = {
        "PEDESTRIAN-VEHICLE PROXIMITY": 1.0,
        "LOITERING": 0.8,
        "CROWD_FORMATION": 0.85,
        "RESTRICTED ZONE ENTRY": 1.0,
        "ABANDONED_OBJECT": 1.0,
    }

    def calculate_risk(self, events: List[Dict], tracked_objects: List[Dict]) -> Tuple[int, str, str, List[Dict]]:
        """Score distinct incidents for this session; score remains until next run."""
        if not events:
            return 0, "LOW", "No rule-based incidents detected", []
        factors = []
        for event in events:
            kind = event.get("type", "UNKNOWN")
            severity = event.get("severity", "MEDIUM").upper()
            points = self.SEVERITY_POINTS.get(severity, 25)
            points = min(100, round(points * self.EVENT_FACTORS.get(kind, 0.8)))
            factors.append({"type": kind, "severity": severity, "contribution": points,
                            "reason": event.get("reason", "")})
        # Many nearby objects can create several alerts of the same rule type.
        # Keep the strongest one per rule and add modest risk for distinct rule
        # categories; duplicate object pairs must not drive a session to 100.
        strongest_by_type = {}
        for factor in factors:
            current = strongest_by_type.get(factor["type"])
            if current is None or factor["contribution"] > current["contribution"]:
                strongest_by_type[factor["type"]] = factor
        ordered = sorted(strongest_by_type.values(), key=lambda item: item["contribution"], reverse=True)
        score = min(100, ordered[0]["contribution"] + 8 * (len(ordered) - 1))
        level = "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MEDIUM" if score >= 25 else "LOW"
        top = ordered[0]
        return score, level, f"Primary concern: {top['type']} ({top['severity']})", factors

    def check_proximity(self, tracked_objects: List[Dict], frame_size=None, threshold_ratio: float = 0.055) -> List[Dict]:
        """Flag close pedestrian/vehicle image-space proximity (not physical distance)."""
        if frame_size:
            threshold = max(35.0, float(np.hypot(*frame_size)) * threshold_ratio)
        else:
            threshold = 60.0
        events = []
        people = [obj for obj in tracked_objects if obj["class"] == "person"]
        vehicles = [obj for obj in tracked_objects if obj["class"] in {"car", "truck", "bus", "motorcycle"}]
        for person in people:
            p = person["bbox"]
            pc = np.asarray(((p[0] + p[2]) / 2, (p[1] + p[3]) / 2))
            for vehicle in vehicles:
                v = vehicle["bbox"]
                vc = np.asarray(((v[0] + v[2]) / 2, (v[1] + v[3]) / 2))
                distance = float(np.linalg.norm(pc - vc))
                if distance < threshold:
                    severity = "CRITICAL" if distance < threshold * 0.15 else "HIGH" if distance < threshold * 0.45 else "MEDIUM"
                    events.append({"type": "PEDESTRIAN-VEHICLE PROXIMITY", "severity": severity,
                                   "object_ids": [person["track_id"], vehicle["track_id"]],
                                   "distance_px": round(distance, 1), "threshold_px": round(threshold, 1),
                                   "reason": f"{person['track_id']} and {vehicle['track_id']} are close in the image ({distance:.0f}px apart)"})
        return events
