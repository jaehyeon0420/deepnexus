# BAAI/bge-reranker-v2-m3 => ONNX 모델 변환 스크립트. 한번만 실행할 것.
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

model_id = "BAAI/bge-reranker-v2-m3"
save_dir = "app/models/bge-reranker-onnx"

model = ORTModelForSequenceClassification.from_pretrained(model_id, export=True)
tokenizer = AutoTokenizer.from_pretrained(model_id)

model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"✅ 'logits'가 포함된 모델로 재변환 완료: {save_dir}")


# ONXX Reranking 테스트 코드
import time
import torch
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

model_dir = "app/models/bge-reranker-onnx"

print("🚀 최적화된 ONNX 모델 로딩 중...")
# 경고 해결을 위해 fix_mistral_regex=True 추가 (지원하는 경우)
tokenizer = AutoTokenizer.from_pretrained(model_dir) 
model = ORTModelForSequenceClassification.from_pretrained(model_dir, provider="CPUExecutionProvider")

pairs = [["검색어 예시입니다.", "문서 내용 예시 1번입니다."] for _ in range(16)]

print(f"⏱️ {len(pairs)}개 문서 Reranking 시작...")
start_time = time.perf_counter()

# 토큰화
inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)

with torch.no_grad():
    # 이제 모델은 'logits'를 반환합니다.
    outputs = model(**inputs)
    # Reranker의 점수는 보통 logits의 첫 번째 값입니다.
    scores = outputs.logits.view(-1,).float().tolist()

end_time = time.perf_counter()
print(f"✅ Reranking 완료! 소요 시간: {end_time - start_time:.4f}초")
print(f"📊 결과 점수(샘플): {scores[:3]}")


# 
from optimum.onnxruntime import ORTQuantizer, ORTModelForSequenceClassification
from optimum.onnxruntime.configuration import AutoQuantizationConfig

model_dir = "app/models/bge-reranker-onnx"
quantized_model_dir = "app/models/bge-reranker-onnx-int8"

# 1. 양자화기 설정
quantizer = ORTQuantizer.from_pretrained(model_dir)
dqconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False) # CPU 최적화 설정

# 2. 양자화 실행 및 저장
quantizer.quantize(
    save_dir=quantized_model_dir,
    quantization_config=dqconfig,
)
print("✅ INT8 양자화 모델 생성 완료!")