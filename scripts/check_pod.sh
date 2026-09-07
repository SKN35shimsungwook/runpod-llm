#!/usr/bin/env bash
# RunPod Pod 상태 점검: 컨테이너 메모리 한도 · 디스크 · GPU · VS Code 서버 강제 종료 흔적
#   bash scripts/check_pod.sh
set -u

human() { if [[ "$1" =~ ^[0-9]+$ ]]; then numfmt --to=iec "$1"; else echo "$1"; fi; }

echo "== 컨테이너 메모리 (cgroup) — free -h 는 호스트 전체 값이라 믿으면 안 됨 =="
if [ -f /sys/fs/cgroup/memory.max ]; then            # cgroup v2
  limit=$(cat /sys/fs/cgroup/memory.max)
  usage=$(cat /sys/fs/cgroup/memory.current)
  peak=$(cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo "?")
else                                                 # cgroup v1
  limit=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
  usage=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
  peak=$(cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes)
fi
echo "한도: $(human "$limit")   사용: $(human "$usage")   최대 기록: $(human "$peak")"
if [[ "$limit" =~ ^[0-9]+$ ]] && [ "$limit" -lt 4000000000 ]; then
  echo "⚠️  한도가 4GB 미만입니다. VS Code 확장 호스트가 SIGKILL 로 죽을 수 있습니다 → 더 큰 사양으로 Pod 재생성 권장"
fi

echo
echo "== 디스크 =="
df -h / /workspace 2>/dev/null

echo
echo "== GPU =="
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv
else
  echo "nvidia-smi 없음 (CPU Pod?)"
fi

echo
echo "== Hugging Face 캐시 위치 =="
echo "HF_HOME=${HF_HOME:-(미설정 → ~/.cache/huggingface, Container Disk 사용)}"

echo
echo "== VS Code 서버 로그: 확장 호스트 강제 종료 횟수 =="
logs=~/.vscode-server/data/logs
if [ -d "$logs" ]; then
  latest="$logs/$(ls -t "$logs" | head -1)"
  kills=$(grep -rh "signal: SIGKILL" "$latest" 2>/dev/null | wc -l)
  echo "최근 세션($latest): SIGKILL $kills 회"
  [ "$kills" -gt 0 ] && echo "⚠️  메모리 한도 초과 가능성 — 위의 컨테이너 메모리 한도를 확인하세요"
else
  echo "VS Code 서버 로그 없음"
fi
