#!/usr/bin/env bash
# 새 Pod 에서 1회 실행합니다.
#   bash setup.sh                      # 기본: /workspace/llm_pod_project
#   PROJECT_DIR=/workspace/xxx bash setup.sh
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=${PROJECT_DIR:-/workspace/llm_pod_project}
MODEL=LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct

echo "① 프로젝트 폴더: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR/outputs"
cd "$PROJECT_DIR"

echo "② uv 가상환경 (이미지의 torch 를 쓰도록 --system-site-packages)"
[ -d .venv ] || uv venv --system-site-packages .venv
grep -q "HF_HOME=" .venv/bin/activate || echo 'export HF_HOME=/workspace/.cache/huggingface' >> .venv/bin/activate
set +u  # activate 스크립트가 정의되지 않은 변수를 참조할 수 있음
# shellcheck disable=SC1091
source .venv/bin/activate
set -u

echo "③ 패키지 설치 (버전 고정)"
uv pip install -r "$SCRIPT_DIR/requirements.txt"

echo "④ uv 가 같이 받은 torch 정리"
bash "$SCRIPT_DIR/fix_torch_conflict.sh"

echo "⑤ EXAONE 다운로드 → $HF_HOME"
if command -v hf >/dev/null; then hf download "$MODEL"; else huggingface-cli download "$MODEL"; fi

echo "⑥ .env 준비 (OPENAI_API_KEY 는 직접 입력, 깃에 올리지 않기)"
[ -f .env ] || echo "OPENAI_API_KEY=" > .env

cp -n "$SCRIPT_DIR"/check_env.py "$SCRIPT_DIR"/check_exaone.py "$SCRIPT_DIR"/first_call_openai.py . || true

echo
echo "✅ 완료. 확인:"
echo "   python check_env.py"
echo "   python check_exaone.py"
