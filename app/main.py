import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


SERVICE_NAME = "cdn-newn-run"
STORAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", "/app/data/images"))


app = FastAPI(
    title="NEWN CDN Storage",
    description="이미지 공유 저장소 상태만 노출하고 파일 직접 접근은 차단하는 내부 저장소 서비스",
    version="1.2.0",
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
        "role": "protected-image-storage",
        "storage_dir": str(STORAGE_DIR),
    }


@app.get("/images/{image_path:path}", summary="이미지 파일 직접 접근 차단")
def block_direct_image_access(image_path: str) -> None:
    raise HTTPException(status_code=403, detail="Use api.newn.run image download API")


@app.get("/static/images/{image_path:path}", summary="정적 이미지 직접 접근 차단")
def block_static_image_access(image_path: str) -> None:
    raise HTTPException(status_code=403, detail="Use api.newn.run image download API")
