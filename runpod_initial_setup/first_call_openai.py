"""Colab Secrets(userdata.get) 대신 .env 에서 키를 읽어 gpt-4o-mini 를 처음 호출합니다.

.env (같은 폴더, 깃에 올리지 않음):
    OPENAI_API_KEY=sk-...
"""
import os
from pathlib import Path

import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit(".env 에 OPENAI_API_KEY 를 넣어 주세요.")

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "당신은 친절한 AI 어시스턴트입니다."},
        {"role": "user", "content": "파인튜닝이 무엇인지 한 문장으로 설명해 주세요."},
    ],
    temperature=0.7,
    max_tokens=200,
)

usage = response.usage
cost = (usage.prompt_tokens * 0.15 + usage.completion_tokens * 0.60) / 1_000_000
print(response.choices[0].message.content)
print(f"\nfinish_reason: {response.choices[0].finish_reason}")
print(f"토큰: 입력 {usage.prompt_tokens} / 출력 {usage.completion_tokens}  →  ${cost:.6f} (약 {cost * 1400:.2f}원)")
