# CIVIS setup guide

## Requirements

- Windows 10/11
- Python 3.11
- Node.js 18 or newer

## Backend

From the CIVIS project root, open PowerShell and run:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main_enhanced.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again.

The API listens on `http://localhost:8000`; health is at `/api/health` and documentation is at `/docs`.

## Frontend

Open a second terminal at the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Try it

Use **Start Demo** to analyze the synthetic crowd clip. The sample library contains five synthetic scenarios, or choose **Upload video** for an MP4, AVI, MOV, or MKV file up to 500 MB. The browser plays an H.264 preview while the backend analyzes the uploaded original.

Sample scenarios illustrate the dashboard and are not realistic surveillance footage. Model detections depend on the video content.

## Models and storage

YOLO runs on CPU by default. Its model weights are stored in `backend/yolov8n.pt`. YuNet face-detection weights are in `models/`; EasyOCR weights are in `backend/models/easyocr/`. Keep the local databases in `backend/` and uploaded footage in `backend/uploads/`.

Face detection reports bounding boxes/counts only. Face recognition and anti-spoofing are not implemented in this version.

## Regenerate synthetic clips

```powershell
python scripts/generate_demo_videos.py
```
