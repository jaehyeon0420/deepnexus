from sentence_transformers import SentenceTransformer

# 1. 모델 로드
model = SentenceTransformer('nlpai-lab/KURE-v1')

# 2. 임베딩 차원수 확인 (get_sentence_embedding_dimension 메서드 사용)
dimension = model.get_sentence_embedding_dimension()

print(f"KURE-v1 모델의 임베딩 차원수: {dimension}")