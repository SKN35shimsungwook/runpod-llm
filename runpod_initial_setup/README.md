# RunPod 초기 설정 (uv 가상환경 · EXAONE · OpenAI)

새 RunPod GPU Pod를 받아서 Day 1 노트북을 돌릴 수 있게 되기까지의 과정과,
그 과정에서 실제로 막혔던 문제·원인·해결을 순서대로 정리했습니다.

```
runpod_initial_setup/
├── README.md              # 이 문서 (설정 순서 + 트러블슈팅)
├── ssh_config.example     # 로컬 PC ~/.ssh/config 에 넣을 RunPod 접속 설정
├── setup.sh               # Pod에서 1회 실행: uv 가상환경 → 패키지 → torch 정리 → 모델 다운로드
├── fix_torch_conflict.sh  # 가상환경에 torch가 또 깔렸을 때 지우는 스크립트
├── requirements.txt       # 오늘 동작 확인한 버전 고정 목록 (torch 제외)
├── check_env.py           # 커널/버전/GPU 점검
├── check_exaone.py        # EXAONE 로드 + 한 문장 생성 테스트
└── first_call_openai.py   # .env 의 OPENAI_API_KEY 로 gpt-4o-mini 첫 호출
```

> 상위 폴더의 `scripts/setup_pod.sh`는 `pip` + 버전 미고정 방식입니다.
> 이 폴더는 **uv** 를 쓰고, 실제로 문제가 났던 패키지 버전을 **고정**한 버전입니다.

---

## 1. 로컬 PC → Pod SSH 접속

RunPod 콘솔 **Connect** 탭의 `SSH over exposed TCP` 값(IP, 포트)을 씁니다.

**cmd**
```
ssh root@<POD_IP> -p <POD_PORT> -i %USERPROFILE%\.ssh\id_ed25519
```

**PowerShell**
```powershell
ssh root@<POD_IP> -p <POD_PORT> -i ~/.ssh/id_ed25519
```

### 겪은 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| `ssh: Could not resolve hostname ssh: 알려진 호스트가 없습니다` (cmd에서는 한글이 `\276\313...`로 깨져 보임) | `ssh ssh root@...` 처럼 `ssh` 를 두 번 입력 → 두 번째 `ssh` 를 호스트 이름으로 해석 | `ssh` 한 번만 입력 |
| cmd에서 `-i ~/.ssh/id_ed25519` 가 키를 못 찾음 | cmd 는 `~` 를 홈 폴더로 바꾸지 않음 | cmd 는 `%USERPROFILE%\.ssh\id_ed25519`, PowerShell 은 `~` 그대로 사용 |
| `Permission denied (publickey)` | 공개키 미등록, 또는 키 등록 전에 만든 Pod | RunPod **Settings → SSH Public Keys** 에 `id_ed25519.pub` 등록 후 Pod 재시작 |

---

## 2. VS Code Remote-SSH 연결

1. 확장 **Remote - SSH** (Microsoft) 설치
2. `ssh_config.example` 내용을 `C:\Users\<사용자>\.ssh\config` 에 넣기 (확장자 없는 파일)
3. `F1` → **Remote-SSH: Connect to Host...** → `runpod` → OS 는 **Linux**
4. **Open Folder** → `/workspace/llm_pod_project`

### 겪은 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 터미널 ssh 는 되는데 VS Code Remotes 목록에 새 Pod 가 없음 | `config` 에 이전 Pod(다른 IP·포트)만 등록돼 있었음 | 새 IP·포트로 `Host runpod` 블록을 고치고 Remotes 패널 새로고침 |
| 다음 날 접속이 안 됨 | Pod 를 새로 만들거나 재시작하면 IP·포트가 바뀔 수 있음 | 콘솔 Connect 탭에서 새 값 확인 → `HostName`, `Port` 만 수정 |

> 파일은 반드시 `/workspace` 아래에 둡니다. Pod 를 재시작해도 남는 곳은 Volume 이 붙은 `/workspace` 뿐입니다.

---

## 3. 프로젝트 폴더 + uv 가상환경

```bash
mkdir -p /workspace/llm_pod_project
cd /workspace/llm_pod_project
uv venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` : RunPod PyTorch 이미지에 이미 깔린 `torch 2.8.0+cu128` / `torchvision 0.23.0+cu128` 을 가상환경에서 그대로 쓰기 위한 옵션입니다.

### 겪은 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 예시 명령을 그대로 붙여넣어 `my_project` 로 만들어짐 | 가이드의 예시 폴더명 | 폴더를 이름만 바꾸지 말고 **다시 만들기** — venv 안의 `activate`·스크립트가 만들 때의 절대경로(`/workspace/my_project/.venv`)를 기억하기 때문 |
| `ls my_project` → `No such file or directory` | 그 사이 VS Code 탐색기에서 폴더 이름을 `llm_pod_project` 로 바꿈 | 바뀐 폴더 안의 `.venv` 는 경로가 깨져 있으므로 `rm -rf .venv` 후 `uv venv` 로 재생성 |
| `A virtual environment already exists at .venv. Do you want to replace it?` | 이미 만든 뒤 같은 명령을 한 번 더 실행 | `y` 로 교체해도 무방 (새 빈 가상환경이 됨) |

---

## 4. 패키지 설치 (버전 고정)

```bash
uv pip install -r requirements.txt
```

| 패키지 | 고정 버전 | 이유 |
|--------|-----------|------|
| `transformers` | `5.1.0` (`<5.2`) | 5.2 부터 내부 인자 이름이 바뀌어 EXAONE 원격 코드(`trust_remote_code=True`)가 `TypeError` 로 깨짐 |
| `openai` | `2.54.0` (`<3`) | 그냥 설치하면 3.x 가 깔림. 수업 노트북은 2.x 기준으로 작성·실행됨 |
| `accelerate` | `1.15.0` | `device_map="auto"` |
| `python-dotenv` | `1.2.4` | Colab Secrets 대신 `.env` 에서 API 키 읽기 |
| `ipykernel` | `7.4.0` | VS Code 노트북 커널로 `.venv` 선택 |

### 겪은 문제 ① — torch 가 가상환경에 또 깔림

`uv pip install transformers accelerate ...` 결과에 `torch==2.14.1`, `triton`, `nvidia-*-cu13`, `cuda-*` 20개가 같이 설치됨.

- 원인: `accelerate` 가 torch 를 요구하는데, **uv 는 `--system-site-packages` 로 보이는 시스템 torch 를 설치된 것으로 치지 않음** → 최신 torch 를 가상환경에 새로 받음
- 결과: `torch.cuda.is_available()` 은 `True` 라서 **정상처럼 보이지만**, torchvision 은 시스템 것(torch 2.8.0 용)을 쓰게 되어 버전이 엇갈림 → 아래 ② 오류

해결 (`fix_torch_conflict.sh`):

```bash
uv pip freeze | grep -E '^(torch|triton|nvidia-|cuda-)' | cut -d= -f1 | xargs -r uv pip uninstall
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__, torch.cuda.is_available())"
# 2.8.0+cu128 0.23.0+cu128 True  ← 이렇게 나와야 정상
```

> Day 3~4 에서 `peft` · `trl` · `bitsandbytes` 를 설치할 때도 같은 일이 생길 수 있습니다.
> 설치 후 매번 위 확인 명령을 실행하고, torch 가 2.8.0 이 아니면 정리 스크립트를 다시 돌립니다.

### 겪은 문제 ② — `RuntimeError: operator torchvision::nms does not exist`

```
File ".../transformers/image_utils.py", line 53
    from torchvision.transforms import InterpolationMode
File "/usr/local/lib/python3.12/dist-packages/torchvision/_meta_registrations.py", line 163
    @torch.library.register_fake("torchvision::nms")
RuntimeError: operator torchvision::nms does not exist
```

- 원인: 가상환경 torch 2.14.1 + 시스템 torchvision 0.23.0(torch 2.8.0 용) 조합
- 해결: ① 의 정리 스크립트로 가상환경 torch 를 지워 시스템 torch 2.8.0 을 쓰게 함

---

## 5. 모델 다운로드 위치를 Volume 으로

```bash
echo 'export HF_HOME=/workspace/.cache/huggingface' >> .venv/bin/activate
source .venv/bin/activate
hf download LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct     # hf 가 없으면 huggingface-cli download ...
```

- 기본 위치 `/root/.cache` 는 컨테이너 디스크라 Pod 를 멈추면 사라질 수 있음
- `~/.bashrc` 대신 **`.venv/bin/activate` 에 추가** → venv 가 `/workspace` 에 있으니 같이 유지되고, 가상환경을 켤 때마다 자동 적용
- `Warning: You are sending unauthenticated requests to the HF Hub` · `hf update` 안내는 무시해도 됨 (공개 모델)

확인:

```bash
python check_exaone.py
# 안녕하세요! 어떻게 도와드릴까요?
```

---

## 6. VS Code 노트북에서 겪은 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| `AttributeError: partially initialized module 'torchvision' has no attribute 'extension' (most likely due to a circular import)` | 같은 커널에서 torchvision import 가 한 번 실패(4-② 오류)한 상태가 메모리에 남음 | 툴바 **Restart** 로 커널 재시작 |
| `NameError: name 'AutoModelForCausalLM' is not defined` | 커널 재시작 후 import 셀을 건너뛰고 모델 로드 셀부터 실행 | 위에서부터 순서대로 실행 (또는 Run All) |
| 어떤 파이썬을 쓰는지 헷갈림 | 커널 선택 문제 | `python check_env.py` 와 같은 내용을 노트북 첫 셀에서 실행해 `sys.executable` 이 `/workspace/llm_pod_project/.venv/bin/python` 인지 확인 |

노트북 첫 셀 점검 코드:

```python
import sys, torch, torchvision, transformers
print(sys.executable)
print(torch.__version__, torchvision.__version__, transformers.__version__)
# /workspace/llm_pod_project/.venv/bin/python
# 2.8.0+cu128 0.23.0+cu128 5.1.0
```

---

## 7. Colab 노트북을 Pod 에서 돌릴 때 바꿀 부분

| Colab 코드 | Pod 에서 |
|------------|----------|
| `!pip install -q --upgrade transformers accelerate` (05 Complete, 06·07·08 EXAONE) | **실행하지 않기.** transformers 가 5.2 이상으로 올라가 EXAONE 이 깨짐. 또 uv 가상환경에는 pip 이 없어서 `!pip` 이 시스템 파이썬에 설치됨 |
| `!pip install -q openai` | 건너뛰기 (이미 설치) |
| `from google.colab import userdata` / `userdata.get("OPENAI_API_KEY")` | `first_call_openai.py` 처럼 `load_dotenv()` + `os.environ["OPENAI_API_KEY"]` |
| `drive.mount(...)`, `/content/drive/MyDrive/...` | 삭제하고 저장 경로를 `/workspace/llm_pod_project/outputs` 로 |
| `/content/sample_output.json` (02 python_basics) | 같은 방식으로 경로 변경 |
| `torch_dtype=torch.bfloat16` | 그대로 동작하지만 경고가 나오면 `dtype=` 으로 |

API 키 읽기:

```python
import os, openai
from dotenv import load_dotenv

load_dotenv("/workspace/llm_pod_project/.env")
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
```

`.env` 는 `OPENAI_API_KEY=...` 한 줄만 직접 입력하고 깃에는 올리지 않습니다.

---

## 8. pyproject.toml 은 만들지 않은 이유

uv 프로젝트 모드(`uv init` / `uv add` / `uv sync`)는 의존성을 풀 때 시스템 torch 를 고려하지 않아서,
`accelerate` 때문에 torch 를 가상환경에 다시 설치하고 4-② 충돌을 다시 만듭니다. `uv sync` 는 목록에 없는 패키지를 지우기도 합니다.
그래서 버전은 `requirements.txt` 로 기록하고 `uv pip install -r` 로 설치합니다.
꼭 `pyproject.toml` 이 필요하면 파일만 두고 설치는 `uv pip install -r pyproject.toml` 로 합니다.

---

## 다음에 접속할 때

```bash
cd /workspace/llm_pod_project
source .venv/bin/activate
```
