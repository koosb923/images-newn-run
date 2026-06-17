#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$PROJECT_ROOT/deploy.log"

ENV_FILE="$PROJECT_ROOT/../.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] images-newn-run 배포 스크립트 시작" >> "$LOG_FILE"

cd "$PROJECT_ROOT" || { echo "이동 실패" >> "$LOG_FILE"; exit 1; }

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Git pull 시작..." >> "$LOG_FILE"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [ -n "$GITHUB_TOKEN" ]; then
        git pull --no-rebase --ff-only https://$GITHUB_TOKEN@github.com/koosb923/images-newn-run.git main >> "$LOG_FILE" 2>&1
    else
        git pull --no-rebase --ff-only origin main >> "$LOG_FILE" 2>&1
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Git 저장소가 아니므로 pull 단계를 생략합니다." >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Docker 빌드 및 배포 시작..." >> "$LOG_FILE"
docker compose -p newn -f "$PROJECT_ROOT/../docker-compose.yml" up -d --build images-app >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Docker 배포 실패" >> "$LOG_FILE"
    tail -n 20 "$LOG_FILE" >&2
    exit 1
fi

docker image prune -f >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] images-newn-run 배포 완료" >> "$LOG_FILE"
