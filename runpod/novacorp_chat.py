"""SSH 터미널에서 바로 쓰는 노바코프 내규 챗봇 (Jupyter 없이 실행).

    python runpod/novacorp_chat.py

명령: /reset 대화 초기화 · /quit 종료
대화 기록은 /workspace/outputs/chat_YYYYMMDD_HHMMSS.jsonl 에 저장된다 (LOG_DIR 로 변경 가능).
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from novacorp import SYSTEM_PROMPT, load_model, stream, trim_history  # noqa: E402

LOG_DIR = Path(os.environ.get("LOG_DIR", "/workspace/outputs"))
MAX_TURNS = int(os.environ.get("MAX_TURNS", "5"))


def main():
    print("📥 EXAONE 로드 중... (첫 실행은 다운로드 때문에 2~3분)")
    tokenizer, model = load_model()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"chat_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("✅ 노바코프 챗봇 준비 완료  (/reset 초기화, /quit 종료)")

    while True:
        try:
            question = input("\n👤 ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question == "/quit":
            break
        if question == "/reset":
            history = history[:1]
            print("🔄 대화가 초기화되었습니다.")
            continue

        history.append({"role": "user", "content": question})
        print("🤖 ", end="", flush=True)
        start = time.perf_counter()
        pieces = []
        for piece in stream(tokenizer, model, trim_history(history, MAX_TURNS)):
            print(piece, end="", flush=True)
            pieces.append(piece)
        seconds = time.perf_counter() - start
        reply = "".join(pieces).strip()
        history.append({"role": "assistant", "content": reply})
        print(f"\n   ({seconds:.1f}s)")

        with log_path.open("a", encoding="utf-8") as f:
            record = {"time": datetime.now().isoformat(timespec="seconds"),
                      "question": question, "answer": reply, "seconds": round(seconds, 2)}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n💾 대화 기록: {log_path}")


if __name__ == "__main__":
    main()
