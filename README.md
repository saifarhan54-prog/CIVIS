# CIVIS

CIVIS is a local computer vision prototype for reviewing public-space video. It detects and tracks objects, counts detected faces without identifying them, reads license plates when visible, and presents heuristic events for human review.

## Project layout

```text
backend/       FastAPI application, CV services, models, uploads, and SQLite data
frontend/      React + Vite dashboard
data/videos/   Five synthetic H.264 scenario clips
models/        YuNet face detection model
scripts/       Setup, model-download, and demo-video tools
```

## Run on Windows

Use two PowerShell terminals from the project root.

Backend:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main_enhanced.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API health check and interactive docs are at `http://localhost:8000/api/health` and `http://localhost:8000/docs`.

## Video analysis

Click **Start Demo** to process the crowd scenario, choose another clip in the sample library, or upload MP4, AVI, MOV, or MKV footage. Uploads are limited to 500 MB. The original file is analyzed, and a browser-compatible H.264 preview is created for playback. Reports, events, and processing status update during the session.

The sample videos are synthetic illustrations. Model detections depend on the actual footage; the synthetic shapes are not guaranteed to be recognized by YOLO.

## Detection capabilities

- YOLO object detection and session-local tracking
- Face detection and counts using OpenCV YuNet; no identity matching or face image storage
- EasyOCR license-plate text detection when the plate is readable
- Behavioral heuristics and configurable zones
- Heuristic risk scoring; results need human review

Face recognition and anti-spoofing are not implemented. Do not use CIVIS alerts as the sole basis for a safety decision.

YuNet weights are from the [OpenCV Zoo model](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) under the MIT license.

## Useful commands

```powershell
# Regenerate all five browser-playable sample clips
python scripts/generate_demo_videos.py

# Build the frontend for deployment
cd frontend
npm run build
```
