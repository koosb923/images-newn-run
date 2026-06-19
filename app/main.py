import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


SERVICE_NAME = "cdn-newn-run"
STORAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", "/app/data/images"))
PUBLIC_DIR = STORAGE_DIR / "public"


app = FastAPI(
    title="NEWN CDN Storage",
    description="공개 이미지와 보호 이미지 저장소를 분리해 제공하는 CDN 서비스",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def ensure_storage_dir() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def resolve_public_image(image_path: str) -> Path:
    requested = (PUBLIC_DIR / image_path).resolve()
    public_root = PUBLIC_DIR.resolve()
    if requested == public_root or public_root not in requested.parents:
        raise HTTPException(status_code=404, detail="Image not found")
    if not requested.is_file() or requested.suffix == ".json":
        raise HTTPException(status_code=404, detail="Image not found")
    return requested


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
        "role": "public-private-image-cdn",
        "storage_dir": str(STORAGE_DIR),
        "public_dir": str(PUBLIC_DIR),
    }


@app.get("/public/{image_path:path}", summary="공개 이미지 파일 조회")
def get_public_image(image_path: str) -> FileResponse:
    return FileResponse(resolve_public_image(image_path))


@app.get("/private/{image_path:path}", summary="비공개 이미지 파일 직접 접근 차단")
def block_private_image_access(image_path: str) -> None:
    raise HTTPException(status_code=403, detail="Use api.newn.run image download API")


@app.get("/images/{image_path:path}", summary="이미지 파일 직접 접근 차단")
def block_direct_image_access(image_path: str) -> None:
    raise HTTPException(status_code=403, detail="Use api.newn.run image download API")


@app.get("/static/images/{image_path:path}", summary="정적 이미지 직접 접근 차단")
def block_static_image_access(image_path: str) -> None:
    raise HTTPException(status_code=403, detail="Use api.newn.run image download API")
