"""커널 · 패키지 버전 · GPU 점검. 노트북 첫 셀에 그대로 붙여 써도 됩니다."""
import sys

import openai
import torch
import torchvision
import transformers

print("python      :", sys.executable)
print("torch       :", torch.__version__)
print("torchvision :", torchvision.__version__)
print("transformers:", transformers.__version__)
print("openai      :", openai.__version__)
print("CUDA        :", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")

problems = []
if ".venv" not in sys.executable:
    problems.append("가상환경(.venv) 파이썬이 아닙니다 → VS Code 커널을 .venv/bin/python 으로 선택")
if not torch.__version__.startswith("2.8.0"):
    problems.append("가상환경에 다른 torch 가 깔렸습니다 → bash fix_torch_conflict.sh")
major, minor = (int(x) for x in transformers.__version__.split(".")[:2])
if (major, minor) >= (5, 2):
    problems.append('transformers 5.2 이상 → uv pip install "transformers<5.2"')
if openai.__version__.startswith("3."):
    problems.append('openai 3.x → uv pip install "openai<3"')

print()
print("\n".join(f"⚠️ {p}" for p in problems) if problems else "✅ 모두 정상")
