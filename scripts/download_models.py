"""Download model weights to the paths used by the active backend."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def download_yolo() -> bool:
    try:
        from ultralytics import YOLO

        os.chdir(BACKEND)
        YOLO("yolov8n.pt")
        print(f"YOLO weights are ready in {BACKEND}")
        return True
    except Exception as exc:
        print(f"YOLO weights unavailable: {exc}")
        return False


def download_ocr() -> bool:
    try:
        import easyocr

        model_dir = BACKEND / "models" / "easyocr"
        easyocr.Reader(
            ["en"], gpu=False, model_storage_directory=str(model_dir),
            user_network_directory=str(model_dir / "user_network"),
            download_enabled=True,
        )
        print(f"EasyOCR weights are ready in {model_dir}")
        return True
    except Exception as exc:
        print(f"EasyOCR weights unavailable: {exc}")
        return False


def main() -> int:
    results = {"YOLO": download_yolo(), "EasyOCR": download_ocr()}
    for name, ready in results.items():
        print(f"{'Ready' if ready else 'Unavailable'}: {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
