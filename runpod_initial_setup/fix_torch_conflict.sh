#!/usr/bin/env bash
# 가상환경에 새로 깔린 torch · triton · nvidia-* · cuda-* 를 지워서
# RunPod 이미지의 torch 2.8.0 + torchvision 0.23.0 조합을 다시 쓰게 합니다.
# (증상: RuntimeError: operator torchvision::nms does not exist)
set -euo pipefail

uv pip freeze | grep -E '^(torch|triton|nvidia-|cuda-)' | cut -d= -f1 | xargs -r uv pip uninstall
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__, torch.cuda.is_available())"
