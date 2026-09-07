#!/usr/bin/env bash
# 새 Pod에서 한 번 실행: HF 캐시를 Volume으로 · 가상환경 · 패키지 · Jupyter 커널 등록
#   git clone https://github.com/SKN35shimsungwook/runpod-llm.git /workspace/runpod-llm
#   bash /workspace/runpod-llm/scripts/setup_pod.sh
set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENV_DIR=${VENV_DIR:-$REPO_DIR/.venv}
HF_CACHE=/workspace/.cache/huggingface

echo "① Hugging Face 캐시를 Volume(/workspace)으로 이동"
mkdir -p "$HF_CACHE" /workspace/outputs
grep -q "HF_HOME=" ~/.bashrc || echo "export HF_HOME=$HF_CACHE" >> ~/.bashrc
export HF_HOME=$HF_CACHE

echo "② 가상환경 생성 (템플릿에 깔린 torch 를 재사용하도록 --system-site-packages)"
[ -d "$VENV_DIR" ] || python -m venv --system-site-packages "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "③ 패키지 설치"
pip install -q --upgrade pip
pip install -q -r "$REPO_DIR/requirements.txt"
python -c "import torch; print('   torch', torch.__version__, '| CUDA', torch.cuda.is_available())"

echo "④ Jupyter 커널 등록 → VS Code 노트북 우측 상단에서 'Python (runpod-llm)' 선택"
python -m ipykernel install --user --name runpod-llm --display-name "Python (runpod-llm)"

echo "⑤ .env 준비 (API 키는 여기에만 넣고 깃에 올리지 않기)"
[ -f "$REPO_DIR/.env" ] || cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"

echo
echo "✅ 완료. 새 터미널을 열거나 'source ~/.bashrc' 후 사용하세요."
echo "   점검:     bash $REPO_DIR/scripts/check_pod.sh"
echo "   챗봇:     python $REPO_DIR/runpod/novacorp_chat.py"
