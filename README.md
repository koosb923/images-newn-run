# images-newn-run

`images.newn.run` 도메인에서 사용할 FastAPI 기반 정적 이미지 오리진 서버입니다.

이미지 업로드/목록/삭제 API는 `api-newn-run`의 `/v1/images`에서 처리하고, 이 서버는 공유 저장소에 저장된 파일을 `/images/...` 경로로 서빙만 합니다.

## 실행 정보

- 서비스명: `images-newn-run`
- Docker compose 서비스명: `images-app`
- 기본 포트: `8507`
- 기본 공개 URL: `https://images.newn.run`
- 기본 저장 경로: `/app/data/images`

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | `https://images.newn.run` | 업로드 응답에 포함할 공개 URL |
| `IMAGE_STORAGE_DIR` | `/app/data/images` | 이미지 저장 경로 |
| `CORS_ALLOW_ORIGINS` | `*` | 쉼표 구분 CORS 허용 origin |

## API

### 헬스체크

```bash
curl http://localhost:8507/health
```

### 이미지 파일 조회

```bash
curl -I https://images.newn.run/images/articles/sample.png
```

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
IMAGE_STORAGE_DIR=./data/images uvicorn app.main:app --host 0.0.0.0 --port 8507 --reload
```

## Docker 실행

```bash
docker build -t images-newn-run .
docker run --rm -p 8507:8507 \
  -e PUBLIC_BASE_URL=https://images.newn.run \
  -v "$PWD/data/images:/app/data/images" \
  images-newn-run
```

통합 compose에 `images-app` 서비스가 있으면 아래 명령으로 배포합니다.

```bash
./deploy.sh
```

## 업로드 API

외부 클라이언트는 이미지 업로드/목록/삭제를 `api-newn-run`으로 요청합니다.

```bash
curl -X POST "https://api.newn.run/v1/images/upload?api_key=$API_KEY" \
  -F "file=@sample.png" \
  -F "folder=articles" \
  -F "alt=sample image"
```

응답의 `image.url`은 `https://images.newn.run/images/...` 형태입니다.

## 자동 배포

`main` 브랜치에 push되면 GitHub webhook이 `https://deploy.newn.run/webhook`으로 전달되고, 중앙 배포 웹훅 서버가 `./deploy.sh`를 실행해 `images-app` 컨테이너를 재빌드/재시작합니다.
