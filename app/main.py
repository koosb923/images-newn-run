import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


SERVICE_NAME = "images-newn-run"
STORAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", "/app/data/images"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://images.newn.run").rstrip("/")

ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".svg": "image/svg+xml",
}


app = FastAPI(
    title="NEWN Image Origin",
    description="images.newn.run 도메인에서 이미지 파일만 정적으로 서빙하는 오리진 서버",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def ensure_storage_dir() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def safe_image_path(image_path: str) -> str:
    normalized = image_path.strip().strip("/")
    if not normalized:
        raise HTTPException(status_code=404, detail="Image not found")
    if not re.fullmatch(r"[a-zA-Z0-9/_.-]+", normalized) or ".." in normalized.split("/"):
        raise HTTPException(status_code=400, detail="Invalid image path")
    if Path(normalized).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Image not found")
    return normalized


@app.on_event("startup")
def startup() -> None:
    ensure_storage_dir()


@app.get("/health", summary="헬스체크")
@app.get("/v1/health", summary="헬스체크")
def health_check() -> dict[str, Any]:
    ensure_storage_dir()
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "role": "static-image-origin",
        "storage_dir": str(STORAGE_DIR),
        "public_base_url": PUBLIC_BASE_URL,
    }


@app.get("/images/{image_path:path}", summary="이미지 파일 조회")
def serve_image(image_path: str) -> FileResponse:
    safe_path = safe_image_path(image_path)
    target = STORAGE_DIR / safe_path
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    content_type = ALLOWED_EXTENSIONS.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(target, media_type=content_type)


app.mount("/static/images", StaticFiles(directory=str(STORAGE_DIR), check_dir=False), name="static-images")
