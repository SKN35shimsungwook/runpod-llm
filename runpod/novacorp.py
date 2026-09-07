"""노바코프 내규 챗봇 공통 모듈 — EXAONE 로드 · 생성 · 스트리밍 · 히스토리 관리.

day1/08_노바코프챗봇_EXAONE.ipynb 의 코드를 RunPod에서 재사용하기 쉽게 모듈로 옮긴 것입니다.
노트북(01_EXAONE_챗봇_응용.ipynb)과 터미널 챗봇(novacorp_chat.py)이 함께 사용합니다.
"""
import os
import time
from threading import Thread

MODEL_NAME = os.environ.get("MODEL_NAME", "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")

NOVACORP_RULES = """
[연차/휴가]
- 정규직: 입사 1년 후 연 15일 유급 연차 / 5년 이상 20일 / 10년 이상 25일
- 연차 신청: 사용일 7일 전까지 부서장 승인 필요
- 병가: 연 10일 유급 (3일 이상은 진단서 필요)
- 결혼 휴가: 본인 5일 / 출산휴가: 90일 (쌍둥이 120일)

[재택근무]
- 주 2일까지 가능 / 3일 전 부서장 승인 필요
- 오전 9시 30분까지 업무 시작 보고 / 회사 VPN 접속 필수
- 신입사원: 입사 후 6개월간 재택 불가

[경비처리]
- 사용일로부터 14일 이내 영수증 제출
- 1회 5만원 초과 식대: 부서장 사전 승인 필요
- 출장 항공권: 이코노미 클래스 한정
- 개인 차량 업무 사용: km당 300원 유류비

[복리후생]
- 연 50만원 복지 포인트 (도서·교육·건강 항목만)
- 결혼 축하금 100만원 / 출산: 첫째 50만원, 둘째 100만원, 셋째 200만원
- 근속 3년마다 안식 휴가 1주일 + 여행 지원금 50만원

[보안]
- 사내 자료 외부 이메일·개인 클라우드 전송 금지
- 비밀번호: 90일마다 변경 / 영문+숫자+특수문자 10자 이상
- 회사 노트북 분실 시 24시간 이내 IT보안팀 신고

[평가/승진]
- 정기 평가: 연 2회 (상·하반기) / S·A·B·C·D 5단계
- 성과급: 평가 등급에 따라 기본급의 0~200%
- 승진 대상: 동일 직급 최소 3년 이상 근무
"""

SYSTEM_PROMPT = f"""당신은 노바코프(Novacorp)의 인사팀 AI 어시스턴트입니다.
직원들의 사내 내규 관련 질문에 정확하고 친절하게 답변하세요.

답변 규칙:
1. 아래 내규 내용만을 근거로 답변하세요
2. 내규에 없는 내용은 "해당 내용은 내규에 명시되어 있지 않습니다. 인사팀에 직접 문의하세요." 라고 안내하세요
3. 답변은 간결하게, 핵심만 전달하세요

=== 노바코프 사내 내규 ===
{NOVACORP_RULES}
"""


def load_model(model_name=MODEL_NAME):
    """토크나이저와 모델을 GPU에 올린다. HF_HOME 을 /workspace 로 두면 Pod 재시작 후에도 재다운로드가 없다."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto",
    )
    model.eval()
    return tokenizer, model


def _encode(tokenizer, model, messages):
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)


def _generation_kwargs(tokenizer, max_new_tokens, temperature, top_p):
    kwargs = {
        "max_new_tokens": max_new_tokens,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
    }
    if temperature > 0:
        kwargs.update(do_sample=True, temperature=temperature, top_p=top_p)
    else:
        kwargs.update(do_sample=False)   # temperature=0 → 그리디 디코딩
    return kwargs


def generate(tokenizer, model, messages, max_new_tokens=300, temperature=0.3, top_p=0.9):
    """한 번에 생성하고 응답 + 속도 지표를 dict로 반환한다."""
    import torch

    input_ids = _encode(tokenizer, model, messages)
    start = time.perf_counter()
    with torch.no_grad():
        output_ids = model.generate(input_ids, **_generation_kwargs(tokenizer, max_new_tokens, temperature, top_p))
    seconds = time.perf_counter() - start

    generated = output_ids[0][input_ids.shape[1]:]
    n_out = len(generated)
    return {
        "content": tokenizer.decode(generated, skip_special_tokens=True).strip(),
        "input_tokens": input_ids.shape[1],
        "output_tokens": n_out,
        "seconds": round(seconds, 2),
        "tokens_per_sec": round(n_out / seconds, 1) if seconds > 0 else 0.0,
        "finish_reason": "length" if n_out >= max_new_tokens else "stop",
    }


def stream(tokenizer, model, messages, max_new_tokens=300, temperature=0.3, top_p=0.9):
    """생성되는 대로 텍스트 조각을 yield 한다. SSH 터미널에서 답을 기다리는 체감 시간이 줄어든다."""
    from transformers import TextIteratorStreamer

    input_ids = _encode(tokenizer, model, messages)
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    kwargs = {"input_ids": input_ids, "streamer": streamer,
              **_generation_kwargs(tokenizer, max_new_tokens, temperature, top_p)}
    thread = Thread(target=model.generate, kwargs=kwargs)
    thread.start()
    for piece in streamer:
        yield piece
    thread.join()


def trim_history(history, max_turns=5):
    """system 메시지는 유지하고 최근 max_turns 턴(user+assistant 쌍)만 남긴다."""
    system = [m for m in history if m["role"] == "system"][:1]
    rest = [m for m in history if m["role"] != "system"]
    return system + rest[-max_turns * 2:]
