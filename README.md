# runpod-llm

SKN35 LLM 과정 실습 노트북을 **RunPod GPU Pod + VS Code(Remote-SSH)** 환경에서 돌리기 위한 저장소입니다.
수업 자료는 Google Colab 기준으로 작성돼 있어서, RunPod에서 실행할 때 달라지는 점과 실제로 겪은 문제 해결 과정을 함께 정리했습니다.

## 폴더 구조

```
runpod-llm/
├── README.md
├── requirements.txt                # openai · transformers · accelerate · python-dotenv · ipykernel
├── .env.example                    # API 키 템플릿 (.env 로 복사, 깃에는 안 올라감)
├── scripts/
│   ├── setup_pod.sh                # 새 Pod 1회 세팅: HF 캐시 → Volume, venv, 패키지, Jupyter 커널
│   └── check_pod.sh                # 메모리 한도(cgroup) · 디스크 · GPU · VS Code SIGKILL 흔적 점검
├── runpod/
│   ├── 00_runpod_환경점검.ipynb      # Colab 01번의 RunPod 버전 점검표
│   ├── 01_EXAONE_챗봇_응용.ipynb     # 08번 챗봇 응용: 속도 측정 · 스트리밍 · 트리밍 · 자동 평가
│   ├── novacorp.py                 # 내규 · system 프롬프트 · EXAONE 로드/생성/스트리밍 공통 모듈
│   └── novacorp_chat.py            # SSH 터미널용 스트리밍 챗봇 (대화 기록 저장)
└── day1/
    ├── 01_colab_setup.ipynb        # 실행 환경 확인 (GPU, pip, 저장소, 세션)
    ├── 02_python_basics.ipynb      # 자료형 · 변수 · 함수 · 딕셔너리 · JSON
    ├── 03_fstring_json_실습.ipynb   # 문자열 메서드 · f-string · json · try/except
    ├── 04_오전실습.ipynb             # 노바코프 HR 챗봇 시나리오 빈칸 채우기
    ├── 05_api_key_자율실습.ipynb     # OpenAI API 첫 호출 · temperature · 토큰 비용 계산
    ├── 06_파라미터실험_{실습,자율실습,EXAONE}.ipynb   # temperature · max_tokens · top_p · 환각 관찰
    ├── 07_멀티턴_{실습,자율실습,EXAONE}.ipynb         # chat() 히스토리 · 안전 호출 · 품질 불일치 관찰
    └── 08_노바코프챗봇_{실습,EXAONE}.ipynb            # 내규 기반 HR 챗봇 v0.1 완성
```

06~08은 같은 주제를 세 가지 버전으로 제공합니다.

- `실습`: OpenAI API(gpt-4o-mini) 강의용
- `자율실습`: 빈칸 채우기 + 정답 코드
- `EXAONE`: HuggingFace `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct`를 GPU에 올려 로컬 추론. **RunPod GPU Pod에서 돌리기 좋은 버전**이고, API 비용이 들지 않습니다.

| 노트북 | 핵심 내용 |
|--------|-----------|
| 01 | `torch.cuda`로 GPU/VRAM 확인, `!pip install`, 저장 경로, 세션 초기화 대응 |
| 02 | LLM 코드에서 쓰는 4가지 자료형, 타입 힌트·기본값 함수, `messages` 중첩 딕셔너리 접근 |
| 03 | `.strip()`/`.replace()`로 코드펜스 제거, 이중 중괄호 `{{}}`, `safe_parse_json`, 지수 백오프 재시도 |
| 04 | 위 내용을 HR 챗봇 미션 7개로 복습 |
| 05 | `openai.OpenAI` 클라이언트, 응답 객체 구조, 역할극 챗봇, gpt-4o-mini 비용 계산 |
| 06 | temperature 4단계 비교, 0.0 반복 동일성, `finish_reason: length`, top_p, 고온에서의 환각 |
| 07 | 싱글턴 vs 멀티턴, `chat()` 4단계, 실패 시 히스토리 복구, 품질 불일치 기록, 컨텍스트 한계 |
| 08 | 내규 데이터 → system 프롬프트 → 멀티턴 → 안전 장치 → 노바코프 챗봇 v0.1 |

---

## RunPod 환경 만들기

### 1. SSH 키 등록 (최초 1회)

로컬 PC에서 공개키를 확인하고 RunPod **Settings → SSH Public Keys**에 붙여넣습니다.

```bash
cat ~/.ssh/id_ed25519.pub
```

키가 없으면 `ssh-keygen -t ed25519`로 먼저 만듭니다.

### 2. Pod 생성 (Pods → Deploy)

| 항목 | 권장값 | 비고 |
|------|--------|------|
| GPU | 수업 지정 GPU | 카드에 표시된 **RAM**이 16GB 이상인지 꼭 확인 |
| Template | `Runpod Pytorch 2.x` | Python · CUDA · Jupyter · SSH 포함 |
| Container Disk | 20GB 이상 | `/root`, `~/.vscode-server`, pip 캐시가 저장됨 |
| Volume Disk | 50GB 정도 | `/workspace`에 마운트, 프로젝트·모델 저장 위치 |
| HTTP 포트 | `8888` | JupyterLab |
| TCP 포트 | `22` | SSH / VS Code 접속에 필수 |

### 3. VS Code로 접속

Pod의 **Connect → SSH over exposed TCP**에 나온 IP와 포트를 `~/.ssh/config`에 등록합니다.

```
Host runpod
  HostName <Pod IP>
  User root
  Port <노출된 TCP 포트>
  IdentityFile ~/.ssh/id_ed25519
```

VS Code → `Remote-SSH: Connect to Host...` → `runpod` 선택 → 폴더는 `/workspace`를 엽니다.
접속 후 Extensions에서 **Python**, **Jupyter**를 `Install in SSH`로 설치해야 `.ipynb`가 열립니다.

### 4. 접속 직후 점검

`bash scripts/check_pod.sh` 한 줄로 아래 항목을 한 번에 볼 수 있습니다(아래 "RunPod 응용" 참고). 수동으로 확인할 때는 이렇게 합니다.

```bash
# 컨테이너에 실제로 할당된 메모리 한도 (free -h는 호스트 전체 값이라 믿으면 안 됨)
cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || cat /sys/fs/cgroup/memory.max

# 디스크
df -h / /workspace

# GPU
nvidia-smi
```

### 5. 프로젝트 · 가상환경

```bash
cd /workspace
mkdir llm_pod_project && cd llm_pod_project
uv init && uv venv && source .venv/bin/activate
uv pip install openai ipykernel torch
```

> 수업 자료의 `(.venv) root@xxxx:/workspace# mkdir ...` 에서 **`#` 앞은 프롬프트**입니다.
> 통째로 복사하면 `bash: syntax error near unexpected token` 이 납니다. `#` 뒤 명령어만 입력하세요.

---

## Colab 노트북을 RunPod에서 돌릴 때 바꿀 것

| Colab | RunPod |
|-------|--------|
| 런타임 → T4 GPU 선택 | Pod 생성 시 GPU 선택 (`nvidia-smi`로 확인) |
| `from google.colab import userdata`<br>`userdata.get("OPENAI_API_KEY")` | `os.environ["OPENAI_API_KEY"]` 또는 `.env` + `python-dotenv` |
| `drive.mount('/content/drive')` | 필요 없음. `/workspace`(Volume)가 Pod 재시작 후에도 유지됨 |
| `/content/...` 경로 | `/workspace/...` 경로 |
| 세션 90분 비활성 종료 | Pod를 Stop 하기 전까지 유지 (대신 켜둔 시간만큼 과금) |

API 키 예시:

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
```

```bash
# 터미널에서 한 번 설정 (키를 노트북·깃에 직접 쓰지 않기)
echo 'export OPENAI_API_KEY=<내 API 키>' >> ~/.bashrc && source ~/.bashrc
```

EXAONE 버전은 모델 가중치를 `~/.cache/huggingface`에 내려받습니다. Container Disk가 작으면 가득 찰 수 있으니 Volume 쪽으로 돌려두세요.

```bash
echo 'export HF_HOME=/workspace/.cache/huggingface' >> ~/.bashrc && source ~/.bashrc
```

> `01_colab_setup.ipynb`의 세션 복구 셀에 남아 있는 `TimeoutException: Requesting secret OPENAI_API_KEY timed out` 출력이 바로 Colab 전용 `userdata`를 Colab UI 밖에서 실행했을 때 나는 에러입니다.

---

## RunPod 응용

### 빠른 시작 (새 Pod에서)

```bash
cd /workspace
git clone https://github.com/SKN35shimsungwook/runpod-llm.git
bash runpod-llm/scripts/setup_pod.sh
source ~/.bashrc
```

`setup_pod.sh`가 하는 일:

1. `HF_HOME=/workspace/.cache/huggingface` 설정. 모델이 Volume에 저장돼 Pod를 재시작해도 다시 받지 않습니다.
2. `--system-site-packages` 가상환경 생성. 템플릿에 설치된 torch(수 GB)를 다시 받지 않고 그대로 씁니다.
3. `requirements.txt` 설치
4. Jupyter 커널 `Python (runpod-llm)` 등록. VS Code 노트북 오른쪽 위에서 선택합니다.
5. `.env.example` → `.env` 복사. API 키는 여기에만 적습니다.

### 상태 점검

```bash
bash scripts/check_pod.sh
```

컨테이너 메모리 한도(`free -h`가 아니라 cgroup 기준), 디스크, GPU, `HF_HOME`, VS Code 확장 호스트 SIGKILL 횟수를 한 번에 보여줍니다.
메모리 한도가 4GB 미만이면 경고합니다. 아래 트러블슈팅의 512MB 사례를 바로 잡아내기 위한 스크립트입니다.

### 노트북

| 노트북 | 내용 |
|--------|------|
| `runpod/00_runpod_환경점검.ipynb` | 가상환경 · GPU · cgroup 메모리 · 디스크 · `HF_HOME` · `.env` 키 로드(값은 출력하지 않음) · 선택적 OpenAI 연결 테스트 |
| `runpod/01_EXAONE_챗봇_응용.ipynb` | 08번 노바코프 챗봇을 `novacorp.py` 모듈로 재사용 → `max_new_tokens`별 tokens/sec 측정 → 스트리밍(첫 글자까지 시간) → 히스토리 트리밍 전후 입력 토큰 비교 → 내규 키워드 9문항 자동 평가 후 `/workspace/outputs/*.jsonl` 저장 → (키가 있으면) GPT-4o-mini와 정확도 비교 → VRAM 정리 |

> 01번은 `runpod/` 폴더에서 실행해야 `from novacorp import ...`가 동작합니다. VS Code에서 노트북을 열면 기본으로 그 폴더에서 실행됩니다.

### 터미널 챗봇 (Jupyter 없이)

```bash
python runpod/novacorp_chat.py
```

- 답변이 생성되는 대로 출력됩니다(스트리밍).
- `/reset`은 대화 초기화, `/quit`은 종료입니다.
- 최근 5턴만 모델에 넣습니다. `MAX_TURNS` 환경변수로 바꿀 수 있습니다.
- 대화 기록은 `/workspace/outputs/chat_*.jsonl`에 저장됩니다. `LOG_DIR` 환경변수로 위치를 바꿀 수 있습니다.

### 운영 팁

| 상황 | 방법 |
|------|------|
| VS Code를 닫아도 작업이 계속 돌게 | `tmux new -s train` 후 실행 → `Ctrl+b d`로 분리, `tmux attach -t train`으로 복귀 |
| 로그를 남기며 백그라운드 실행 | `nohup python script.py > /workspace/outputs/run.log 2>&1 &` |
| GPU 사용률 실시간 확인 | `watch -n 1 nvidia-smi` |
| 결과물 로컬로 받기 | 로컬에서 `scp -r runpod:/workspace/outputs ./outputs` |
| 비용 아끼기 | 실습이 끝나면 **Stop**. 켜져 있는 시간만큼 과금되고, Stop 상태에서는 Volume 저장 비용만 나갑니다 |

---

## 트러블슈팅 기록

### `.ipynb`가 안 열림: "Unable to open ... Canceled"

**증상**
- VS Code에서 노트북을 열면 `Unable to open '[day1]01.colab_setup.ipynb' — Canceled`
- 상태바에 `The remote extension host terminated unexpectedly. Restarting...` 반복

**확인 과정**

1. 디스크·메모리 확인 → `df -h`는 15%, `free -h`는 251Gi 중 163Gi 여유로 **정상처럼 보임**
2. 서버 로그 확인
   ```bash
   L=~/.vscode-server/data/logs/$(ls -t ~/.vscode-server/data/logs | head -1)
   grep -riE "error|exit|SIGKILL" $L --include=*.log | tail -40
   ```
   - `exthost*/remoteexthost.log` : `EEXIST: file already exists, open '.../workspaceStorage/<hash>/vscode.lock'`
   - `remoteagent.log` : `Extension Host Process exited with code: null, signal: SIGKILL.` (뜬 지 20~30초 만에 반복)
3. 컨테이너 cgroup 메모리 확인
   ```
   memory.limit_in_bytes      512000000   ← 한도 약 512MB
   memory.max_usage_in_bytes  512004096   ← 한도에 도달한 기록
   ```

**원인**
- Pod 컨테이너 메모리 한도가 **512MB**였음. `free -h`는 호스트 전체 메모리를 보여줘서 착각하기 쉬움.
- JupyterLab + VS Code 서버만으로 약 300MB 사용 → 확장 호스트(Jupyter, Copilot)가 올라오면 한도 초과 → 커널이 SIGKILL.
- `vscode.lock` 에러는 원인이 아니라 강제 종료 후 남은 잠금 파일(부산물). VS Code가 stale lock을 스스로 지우고 있었음.

**해결**
- RAM이 충분한 사양으로 Pod를 새로 생성 (위 "Pod 생성" 표 참고). 생성 직후 cgroup 메모리 한도부터 확인.
- 임시 방편: VS Code 대신 RunPod **Connect → Jupyter Lab**(8888)으로 노트북 사용, 원격 Copilot 비활성화.
- 꼬인 서버 정리가 필요할 때:
  ```bash
  # VS Code 창을 모두 닫은 뒤
  pkill -f vscode-server
  rm -f ~/.vscode-server/data/User/workspaceStorage/*/vscode.lock
  ```
  그래도 안 되면 `Ctrl+Shift+P` → `Remote-SSH: Kill VS Code Server on Host...` 또는 `rm -rf ~/.vscode-server` 후 재접속.

### Pod 정리

- 새 Pod 확인 후 기존 Pod는 **Stop → Terminate**. Stop만 하면 Volume 저장 비용이 계속 나감.
- `/root`(Container Disk)는 재시작 시 초기화되므로 작업 파일은 항상 `/workspace`에 둘 것.
