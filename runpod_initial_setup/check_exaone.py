"""EXAONE 을 GPU 에 올려 한 문장 생성까지 되는지 확인합니다."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL, dtype=torch.bfloat16, trust_remote_code=True, device_map="auto"
)
print(f"GPU 메모리: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")

prompt = tokenizer.apply_chat_template(
    [{"role": "user", "content": "한 문장으로 인사해줘"}],
    tokenize=False,
    add_generation_prompt=True,
)
input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to("cuda")
output_ids = model.generate(
    input_ids, max_new_tokens=40, do_sample=False, eos_token_id=tokenizer.eos_token_id
)
print(tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True))
