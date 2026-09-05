# runpod-llm

SKN35 LLM 과정 실습 노트북을 **RunPod GPU Pod + VS Code(Remote-SSH)** 환경에서 돌리기 위한 저장소입니다.
수업 자료는 Google Colab 기준으로 작성돼 있어서, RunPod에서 실행할 때 달라지는 점과 실제로 겪은 문제 해결 과정을 함께 정리했습니다.

## 폴더 구조

```
runpod-llm/
├── README.md
└── day1/
    ├── 01_colab_setup.ipynb        # 실행 환경 확인 (GPU, pip, 저장소, 세션)
    ├── 02_python_basics.ipynb      # 자료형 · 변수 · 함수 · 딕셔너리 · JSON
    ├── 03_fstring_json_실습.ipynb   # 문자열 메서드 · f-string · json · try/except
    ├── 04_오전실습.ipynb             # 노바코프 HR 챗봇 시나리오 빈칸 채우기
    └── 05_api_key_자율실습.ipynb     # OpenAI API 첫 호출 · temperature · 토큰 비용 계산
```

| 노트북 | 핵심 내용 |
|--------|-----------|
| 01 | `torch.cuda`로 GPU/VRAM 확인, `!pip install`, 저장 경로, 세션 초기화 대응 |
| 02 | LLM 코드에서 쓰는 4가지 자료형, 타입 힌트·기본값 함수, `messages` 중첩 딕셔너리 접근 |
| 03 | `.strip()`/`.replace()`로 코드펜스 제거, 이중 중괄호 `{{}}`, `safe_parse_json`, 지수 백오프 재시도 |
| 04 | 위 내용을 HR 챗봇 미션 7개로 복습 |
| 05 | `openai.OpenAI` 클라이언트, 응답 객체 구조, 역할극 챗봇, gpt-4o-mini 비용 계산 |

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

> `01_colab_setup.ipynb`의 세션 복구 셀에 남아 있는 `TimeoutException: Requesting secret OPENAI_API_KEY timed out` 출력이 바로 Colab 전용 `userdata`를 Colab UI 밖에서 실행했을 때 나는 에러입니다.

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
