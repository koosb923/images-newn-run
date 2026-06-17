import json
import os
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


SERVICE_NAME = "images-newn-run"
STORAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", "/app/data/images"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://images.newn.run").rstrip("/")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
API_KEY = os.getenv("IMAGE_SERVER_API_KEY", "")

ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".svg": "image/svg+xml",
}
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


app = FastAPI(
    title="NEWN Image Server",
    description="images.newn.run 도메인에서 사용할 이미지 업로드 및 정적 서빙 서버",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class ImageMeta(BaseModel):
    id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    folder: str = ""
    alt: str = ""
    url: str
    created_at: str


class ImageListResponse(BaseModel):
    total: int
    images: list[ImageMeta]


class UploadResponse(BaseModel):
    status: str = "success"
    image: ImageMeta


def ensure_storage_dir() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if API_KEY and not secrets.compare_digest(x_api_key or "", API_KEY):
        raise HTTPException(status_code=401, detail="Invalid image server API key")


def safe_folder(folder: str | None) -> str:
    if not folder:
        return ""
    normalized = folder.strip().strip("/")
    if not normalized:
        return ""
    if not re.fullmatch(r"[a-zA-Z0-9/_-]+", normalized) or ".." in normalized.split("/"):
        raise HTTPException(status_code=400, detail="folder can only contain letters, numbers, slash, dash, and underscore")
    return normalized


def safe_image_path(image_path: str) -> str:
    normalized = image_path.strip().strip("/")
    if not normalized:
        raise HTTPException(status_code=404, detail="Image not found")
    if not re.fullmatch(r"[a-zA-Z0-9/_.-]+", normalized) or ".." in normalized.split("/"):
        raise HTTPException(status_code=400, detail="Invalid image path")
    if Path(normalized).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Image not found")
    return normalized


def image_url(filename: str, folder: str = "") -> str:
    path = f"{folder}/{filename}" if folder else filename
    return f"{PUBLIC_BASE_URL}/images/{path}"


def meta_path(image_path: Path) -> Path:
    return image_path.with_suffix(f"{image_path.suffix}.json")


def write_meta(image_path: Path, meta: ImageMeta) -> None:
    meta_path(image_path).write_text(json.dumps(meta.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")


def read_meta(path: Path) -> ImageMeta | None:
    try:
        return ImageMeta.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def resolve_image_by_id(image_id: str) -> tuple[Path, ImageMeta] | None:
    ensure_storage_dir()
    for meta_file in STORAGE_DIR.rglob("*.json"):
        meta = read_meta(meta_file)
        if meta and meta.id == image_id:
            image_path = meta_file.with_suffix("")
            if image_path.exists():
                return image_path, meta
    return None


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
        "storage_dir": str(STORAGE_DIR),
        "public_base_url": PUBLIC_BASE_URL,
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "auth_enabled": bool(API_KEY),
    }


@app.post("/v1/images", response_model=UploadResponse, dependencies=[Depends(require_api_key)], summary="이미지 업로드")
async def upload_image(
    file: UploadFile = File(...),
    folder: str | None = Form(default=None),
    alt: str = Form(default=""),
) -> UploadResponse:
    ensure_storage_dir()
    original_name = file.filename or "image"
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported image extension: {extension or '(none)'}")

    expected_type = ALLOWED_EXTENSIONS[extension]
    if file.content_type and file.content_type != expected_type:
        if not (extension in {".jpg", ".jpeg"} and file.content_type == "image/jpeg"):
            raise HTTPException(status_code=400, detail=f"Content-Type must be {expected_type}")

    target_folder = safe_folder(folder)
    target_dir = STORAGE_DIR / target_folder if target_folder else STORAGE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    image_id = secrets.token_urlsafe(12)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{image_id}{extension}"
    image_path = target_dir / filename

    size = 0
    try:
        with image_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    output.close()
                    image_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"Image exceeds {MAX_UPLOAD_SIZE_MB}MB limit")
                output.write(chunk)
    finally:
        await file.close()

    meta = ImageMeta(
        id=image_id,
        filename=filename,
        original_filename=original_name,
        content_type=expected_type,
        size_bytes=size,
        folder=target_folder,
        alt=alt,
        url=image_url(filename, target_folder),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    write_meta(image_path, meta)
    return UploadResponse(image=meta)


@app.get("/v1/images", response_model=ImageListResponse, summary="이미지 목록")
def list_images(limit: int = Query(default=100, ge=1, le=500), folder: str | None = None) -> ImageListResponse:
    ensure_storage_dir()
    target_folder = safe_folder(folder)
    base_dir = STORAGE_DIR / target_folder if target_folder else STORAGE_DIR
    images = [
        meta
        for meta_file in sorted(base_dir.rglob("*.json"), reverse=True)
        if (meta := read_meta(meta_file)) is not None
    ]
    return ImageListResponse(total=len(images), images=images[:limit])


@app.get("/v1/images/{image_id}", response_model=ImageMeta, summary="이미지 메타데이터 조회")
def get_image(image_id: str) -> ImageMeta:
    found = resolve_image_by_id(image_id)
    if not found:
        raise HTTPException(status_code=404, detail="Image not found")
    return found[1]


@app.delete("/v1/images/{image_id}", dependencies=[Depends(require_api_key)], summary="이미지 삭제")
def delete_image(image_id: str) -> dict[str, str]:
    found = resolve_image_by_id(image_id)
    if not found:
        raise HTTPException(status_code=404, detail="Image not found")
    image_path, _ = found
    image_path.unlink(missing_ok=True)
    meta_path(image_path).unlink(missing_ok=True)
    return {"status": "deleted", "id": image_id}


@app.get("/images/{image_path:path}", summary="이미지 파일 조회")
def serve_image(image_path: str) -> FileResponse:
    safe_path = safe_image_path(image_path)
    target = STORAGE_DIR / safe_path
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    content_type = ALLOWED_EXTENSIONS.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(target, media_type=content_type)


app.mount("/static/images", StaticFiles(directory=str(STORAGE_DIR), check_dir=False), name="static-images")
