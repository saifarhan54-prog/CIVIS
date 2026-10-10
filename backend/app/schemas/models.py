"""Request schemas used by the CIVIS API."""
from typing import Literal

from pydantic import BaseModel


class AnalysisStart(BaseModel):
    source: Literal["upload", "demo"] = "demo"
    demo_mode: bool = True
    video_path: str | None = None
