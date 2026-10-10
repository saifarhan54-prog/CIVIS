"""
CIVIS Enhanced - Main Application
Complete surveillance system with multi-modal AI
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess
import cv2
import numpy as np

# Import our services
from services.detection_service import DetectionService
from services.tracking_service import TrackingService
from services.behavioral_service import BehavioralAnalyzer
from services.risk_engine import RiskEngine
from services.alpr_service import ALPRService
from services.face_service import FaceRecognitionService
from database.db_manager import DatabaseManager
from config.settings import settings
from app.schemas.models import AnalysisStart

# Initialize services
detector = DetectionService()
tracker = TrackingService()
behavioral = BehavioralAnalyzer()
risk_engine = RiskEngine()
alpr = ALPRService()
face_recognizer = FaceRecognitionService()
db = DatabaseManager()

# Application state
app_state = {
    "processing": False,
    "current_video": None,
    "frame_count": 0,
    "fps": 0,
    "total_objects": 0,
    "face_detections": 0,
    "active_alerts": 0,
    "risk_score": 0,
    "risk_level": "LOW",
    "risk_reason": "No rule-based incidents detected",
    "unique_objects": 0,
    "objects_by_class": {},
    "current_objects_by_class": {},
    "video_duration_seconds": 0,
    "frame_width": 0,
    "frame_height": 0,
    "current_detections": [],
}
run_events = []
last_report = {
    "title": "Analysis report",
    "summary": "Start a demo or analyze a video to generate a report.",
    "highlights": [],
    "is_demo": False,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("🚀 CIVIS Enhanced starting...")
    db.init_database()
    print("✅ Database initialized")
    yield
    print("👋 CIVIS Enhanced shutting down...")

app = FastAPI(
    title="CIVIS Enhanced API",
    version="2.0.0",
    description="Computer Vision Intelligence for Public Safety",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/outputs", StaticFiles(directory=settings.OUTPUTS_DIR), name="outputs")
app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")
app.mount("/demo-videos", StaticFiles(directory=settings.BASE_DIR.parent / "data" / "videos"), name="demo-videos")

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CIVIS Enhanced",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "modules": {
            "detection": detector.model is not None,
            "tracking": True,
            "alpr": alpr.reader is not None,
            "face_recognition": False,
            "anti_spoofing": False,
            "face_detection": face_recognizer.available,
            "behavioral": True,
            "risk_assessment": True,
        }
    }

@app.post("/api/video/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video for processing"""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".avi", ".mov", ".mkv"]:
        raise HTTPException(400, "Invalid file type. Use MP4, AVI, MOV, or MKV")
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{Path(file.filename).name}"
    filepath = settings.UPLOADS_DIR / filename
    
    with filepath.open("wb") as f:
        content = await file.read()
        if not content:
            filepath.unlink(missing_ok=True)
            raise HTTPException(400, "The uploaded video is empty.")
        if len(content) > 500 * 1024 * 1024:
            filepath.unlink(missing_ok=True)
            raise HTTPException(413, "Video is too large. The maximum upload size is 500 MB.")
        f.write(content)

    # OpenCV accepts more codecs than browsers. Store a small H.264 preview beside
    # the original so playback works while analysis continues on the source file.
    preview_name = f"{filepath.stem}.preview.mp4"
    preview_path = settings.UPLOADS_DIR / preview_name
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        await asyncio.to_thread(subprocess.run, [
            ffmpeg, "-y", "-i", str(filepath), "-an", "-vf", "scale='min(1280,iw)':-2",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(preview_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        preview_path.unlink(missing_ok=True)
        preview_name = None
    
    return {
        "filename": filename,
        "path": str(filepath),
        "size": len(content),
        "preview_url": f"/uploads/{preview_name}" if preview_name else None,
        "message": "Video uploaded successfully"
    }

@app.post("/api/analysis/start")
async def start_analysis(body: AnalysisStart):
    """Start video analysis"""
    global app_state, run_events, last_report
    
    if app_state["processing"] and app_state.get("current_video") != "demo":
        raise HTTPException(409, "An analysis is already running. Stop it before starting another.")

    if body.demo_mode or body.source == "demo":
        # Create demo events
        with db.get_connection() as conn:
            conn.execute("DELETE FROM events WHERE is_demo = 1")
        demo_events = [
            {
                "type": "RESTRICTED ZONE ENTRY",
                "severity": "MEDIUM",
                "object_ids": ["PERSON_12"],
                "reason": "PERSON_12 entered restricted area",
                "is_demo": True
            },
            {
                "type": "CROWD_FORMATION", 
                "severity": "MEDIUM",
                "object_ids": ["PERSON_12", "PERSON_18", "PERSON_21"],
                "reason": "Crowd of 12 people detected (threshold: 10)",
                "is_demo": True
            },
            {
                "type": "PEDESTRIAN-VEHICLE PROXIMITY",
                "severity": "HIGH",
                "object_ids": ["PERSON_12", "VEHICLE_04"],
                "reason": "PERSON_12 and VEHICLE_04 within 6.2m, converging trajectories",
                "is_demo": True
            }
        ]
        
        for event in demo_events:
            event["timestamp"] = datetime.utcnow().isoformat()
            event["id"] = db.add_event(event)
        run_events = list(demo_events)
        last_report = build_report(is_demo=True)
        
        app_state.update({
            "processing": False,
            "current_video": "demo",
            "fps": 18.4,
            "total_objects": 15,
            "unique_objects": 15,
            "objects_by_class": {"person": 12, "car": 3},
            "current_objects_by_class": {"person": 12, "car": 3},
            "active_alerts": 3,
            "risk_reason": "Simulated demo events",
            "video_duration_seconds": 0,
            "current_detections": [],
        })
        
        # Calculate risk
        risk_score, risk_level, reason, factors = risk_engine.calculate_risk(demo_events, [])
        app_state.update({
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reason": reason,
        })
        
        return {"status": "started", "mode": "demo", "state": app_state}
    
    # Real video processing
    video_path = str(settings.UPLOADS_DIR / Path(body.video_path).name) if body.video_path else None
    if not video_path or not Path(video_path).is_file():
        raise HTTPException(404, "Uploaded video not found. Upload a video before starting analysis.")
    probe = cv2.VideoCapture(video_path)
    readable = probe.isOpened()
    probe.release()
    if not readable:
        raise HTTPException(422, "The uploaded file could not be opened as a video. Export it as MP4 (H.264) and upload again.")
    
    app_state.update({
        "processing": True,
        "current_video": video_path,
        "frame_count": 0,
        "active_alerts": 0,
        "total_objects": 0,
        "face_detections": 0,
        "risk_score": 0,
        "risk_level": "LOW",
        "risk_reason": "No rule-based incidents detected",
        "unique_objects": 0,
        "objects_by_class": {},
        "current_objects_by_class": {},
        "video_duration_seconds": 0,
        "frame_width": 0,
        "frame_height": 0,
        "current_detections": [],
    })
    run_events = []
    last_report = {
        "title": "Video analysis report",
        "summary": "The video is being processed. The report will update when analysis finishes.",
        "highlights": [],
        "is_demo": False,
    }
    tracker.tracks.clear()
    tracker.id_prefix.clear()
    behavioral.reset()
    
    # Start background processing
    asyncio.create_task(process_video(video_path))
    
    return {"status": "started", "video": video_path, "state": app_state}

@app.post("/api/analysis/stop")
async def stop_analysis():
    """Stop video analysis"""
    global app_state
    app_state["processing"] = False
    return {"status": "stopped", "state": app_state}

@app.get("/api/analysis/status")
async def get_status():
    """Get current analysis status"""
    return app_state

@app.get("/api/analysis/report")
async def get_analysis_report():
    return last_report

def build_report(is_demo=False):
    if is_demo:
        return {
            "title": "Demo report",
            "summary": "This demo shows three simulated safety signals: a restricted-zone entry, a crowd-density alert, and pedestrian–vehicle proximity. The illustrative risk score is 44/100 (MEDIUM). These are sample events, not detections from a video.",
            "highlights": ["3 simulated incidents", "Highest severity: HIGH", "Human review required"],
            "is_demo": True,
        }

    event_count = len(run_events)
    highest = max(run_events, key=lambda event: {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(event.get("severity"), 0), default=None)
    frames = app_state.get("frame_count", 0)
    objects = app_state.get("unique_objects", 0)
    object_counts = app_state.get("objects_by_class", {})
    faces = app_state.get("face_detections", 0)
    risk = app_state.get("risk_score", 0)
    duration = app_state.get("video_duration_seconds", 0)
    inventory = ", ".join(f"{count} {name}{'s' if count != 1 else ''}" for name, count in sorted(object_counts.items())) or "no objects confidently detected"
    if app_state.get("processing"):
        summary = f"Analyzing {duration:.1f}s of footage: {frames} frames read and {objects} unique tracked objects ({inventory}). {event_count} distinct incident rule(s) have been triggered so far."
    else:
        summary = f"Analyzed {duration:.1f}s of footage across {frames} frames. Detected {objects} unique tracked objects ({inventory}) and recorded {event_count} distinct rule-based incident(s). Session risk: {risk}/100 ({app_state.get('risk_level', 'LOW')})."
    highlights = [f"Video duration: {duration:.1f}s", f"Frames read: {frames}", f"Unique tracked objects: {objects}", f"Object classes: {inventory}", f"Session risk: {risk}/100 ({app_state.get('risk_level', 'LOW')})", f"Face detections: {faces} (no identity matching)"]
    if highest:
        highlights.insert(1, f"Highest alert: {highest.get('type')} ({highest.get('severity')})")
    if event_count:
        incident_types = sorted({event.get("type", "UNKNOWN") for event in run_events})
        summary += f" Incident assessment: {', '.join(incident_types)}."
        highlights.extend(f"Incident: {kind}" for kind in incident_types)
        summary += " Incident labels are rule-based indicators and require human review. Proximity is measured in image pixels, not real-world distance."
    else:
        summary += " No configured incident rule was triggered; this does not establish that a scene is safe."
    return {"title": "Video analysis report", "summary": summary, "highlights": highlights, "is_demo": False}

@app.get("/api/events")
async def get_events(limit: int = 50):
    """Return events from the active/latest session, not historic database rows."""
    return list(reversed(run_events[-max(1, min(limit, 500)):]))

@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    """Get specific event details"""
    event = db.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    return event

@app.get("/api/statistics")
async def get_statistics():
    """Get system statistics"""
    events = db.get_events(limit=1000)
    
    stats = {
        "objects": {
            "people": sum(1 for e in events if "PERSON" in str(e.get("object_ids", []))),
            "vehicles": sum(1 for e in events if "VEHICLE" in str(e.get("object_ids", []))),
            "total": app_state.get("total_objects", 0)
        },
        "events": {
            "proximity": sum(1 for e in events if e["type"] == "PEDESTRIAN-VEHICLE PROXIMITY"),
            "loitering": sum(1 for e in events if e["type"] == "LOITERING"),
            "crowd": sum(1 for e in events if e["type"] == "CROWD_FORMATION"),
            "zone_violation": sum(1 for e in events if "ZONE" in e["type"]),
            "total": len(events)
        },
        "risk": {
            "current_score": app_state.get("risk_score", 0),
            "current_level": app_state.get("risk_level", "LOW"),
            "active_alerts": app_state.get("active_alerts", 0)
        },
        "performance": {
            "fps": app_state.get("fps", 0),
            "frames_processed": app_state.get("frame_count", 0)
        }
    }
    
    return stats

@app.get("/api/zones")
async def get_zones():
    """Get configured zones"""
    return db.get_zones()

@app.post("/api/zones")
async def create_zone(zone_data: dict):
    """Create new monitoring zone"""
    zone_id = db.add_zone(zone_data)
    return {"id": zone_id, **zone_data}

@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: int):
    """Delete zone"""
    db.delete_zone(zone_id)
    return {"deleted": zone_id}

@app.get("/api/vehicles")
async def get_vehicles():
    """Get detected vehicles"""
    return db.get_vehicles()

@app.get("/api/faces")
async def get_faces():
    """Get recognized faces"""
    return db.get_faces()

# =============================================================================
# VIDEO PROCESSING PIPELINE
# =============================================================================

async def process_video(video_path: str):
    """Main video processing pipeline"""
    global app_state, last_report
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        app_state["processing"] = False
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    if not np.isfinite(fps) or fps <= 0:
        fps = 30
    frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    session_objects = {}
    frame_count = 0
    
    print(f"▶️  Processing video: {video_path}")
    print(f"   FPS: {fps}, Total frames: {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}")
    
    try:
        while app_state["processing"]:
            ret, frame = cap.read()
            if not ret:
                break
        
            frame_count += 1
        
        # Process every Nth frame to maintain performance
            if frame_count % 3 != 0:
                continue
        
        # 1. Object Detection
            detections = detector.detect(frame)
        
        # 2. Object Tracking
            tracked_objects = tracker.update(detections)
        
        # 3. ALPR for vehicles
            vehicles = [obj for obj in tracked_objects if obj["class"] in ["car", "truck", "bus", "motorcycle"]]
            if vehicles and alpr.reader and frame_count % 30 == 0:
                vehicle_bboxes = [obj["bbox"] for obj in vehicles]
                plates = alpr.detect_plates(frame, vehicle_bboxes)
            
            # Store detected plates
                for plate_info in plates:
                    db.add_vehicle(plate_info)
        
        # 4. Face detection only. No images or face templates are stored.
            face_detections = face_recognizer.detect_faces(frame) if face_recognizer.available else []
        
        # 5. Behavioral Analysis uses source-video time, not processing wall time.
            video_time = frame_count / fps
            height, width = frame.shape[:2]
            behavioral_events = behavioral.analyze(tracked_objects, video_time, (width, height))
        
        # 6. Proximity Detection
            proximity_events = risk_engine.check_proximity(tracked_objects, (width, height))
        
        # 7. Combine all events
            all_events = behavioral_events + proximity_events

        # 7. Configured restricted zones use normalized coordinates (pixel coordinates also accepted).
            for zone in db.get_zones():
                if not zone.get("enabled", True) or "restrict" not in zone.get("zone_type", "").lower():
                    continue
                zx, zy, zw, zh = (float(zone.get(key, 0) or 0) for key in ("x", "y", "width", "height"))
                if max(abs(zx), abs(zy), abs(zw), abs(zh)) > 1:
                    zx, zw = zx / width, zw / width
                    zy, zh = zy / height, zh / height
                for obj in tracked_objects:
                    if obj["class"] != "person":
                        continue
                    x1, y1, x2, y2 = obj["bbox"]
                    nx, ny = (x1 + x2) / (2 * width), (y1 + y2) / (2 * height)
                    if zx <= nx <= zx + zw and zy <= ny <= zy + zh:
                        all_events.append({"type": "RESTRICTED ZONE ENTRY", "severity": "HIGH",
                                           "object_ids": [obj["track_id"]], "zone": zone.get("name", "Restricted zone"),
                                           "reason": f"{obj['track_id']} detected inside restricted zone '{zone.get('name', 'Restricted zone')}'"})
        
        # 8. Store events in database
            for event in all_events:
                event_key = (event.get("type"), tuple(event.get("object_ids", [])))
                if not any((existing.get("type"), tuple(existing.get("object_ids", []))) == event_key for existing in run_events):
                    event["timestamp"] = datetime.utcnow().isoformat()
                    event["video_time"] = round(video_time, 2)
                    event["risk_score"] = risk_engine.calculate_risk([event], tracked_objects)[0]
                    event["id"] = db.add_event(event)
                    run_events.append(event)
        
        # 9. Calculate risk score
            risk_score, risk_level, reason, factors = risk_engine.calculate_risk(
                run_events, tracked_objects
            )

        # Maintain session inventory by unique tracker ID, and latest-frame class counts.
            for obj in tracked_objects:
                session_objects[obj["track_id"]] = obj["class"]
            object_counts = {}
            for class_name in session_objects.values():
                object_counts[class_name] = object_counts.get(class_name, 0) + 1
            current_counts = {}
            for obj in tracked_objects:
                current_counts[obj["class"]] = current_counts.get(obj["class"], 0) + 1
        
        # 10. Update state
            app_state.update({
                "frame_count": frame_count,
                "fps": fps,
                "total_objects": len(tracked_objects),
                "unique_objects": len(session_objects),
                "objects_by_class": object_counts,
                "current_objects_by_class": current_counts,
                "video_duration_seconds": round(frame_count / fps, 1),
                "frame_width": width,
                "frame_height": height,
                "face_detections": len(face_detections),
                "active_alerts": len(run_events),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_reason": reason,
                "current_detections": [{"track_id": o["track_id"], "class": o["class"],
                                         "confidence": round(float(o.get("confidence", 0)), 3),
                                         "bbox": list(o["bbox"])} for o in tracked_objects],
            })
            last_report = build_report()
        
        # Small delay to prevent CPU overload
            await asyncio.sleep(0.01)
    finally:
        cap.release()
        app_state["processing"] = False
        last_report = build_report()
    print(f"✅ Video processing completed. Processed {frame_count} frames")

# =============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send current state to client
            await websocket.send_json(app_state)
            await asyncio.sleep(1)  # Update every second
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
