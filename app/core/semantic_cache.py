import redis
import numpy as np
from redis.commands.search.query import Query
import time
from typing import Optional, List
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from app.services.llm import get_embeddings

class SemanticCacheManager:
    def __init__(self, redis_client: redis.Redis):
        # Redis Client
        self.r = redis_client
        self.index_name = "idx:semantic_cache"
        # KURE-v1 임베딩 모델 기준
        self.vector_dim = 1024 
        # 유사도 기준 (0.1 거리 = 약 90% 유사도)
        self.distance_threshold = 0.1
        
        # 임베딩 모델 초기화
        self.embeddings = get_embeddings()
        print('semantic init!!')
        # 인덱스 확인 및 생성
        self._create_index()

    def _create_index(self):
        try:
            self.r.ft(self.index_name).info()
            print(f"✅ [Semantic Cache] 인덱스 '{self.index_name}'가 이미 존재합니다.")
        except Exception as e:
            # 인덱스가 없는 것인지, 아니면 Redis가 Search를 지원 안 하는지 확인
            print(f"🔍 [Semantic Cache] 인덱스 확인 중 참고사항: {e}")
            try:
                schema = (
                    TextField("response_text"),
                    VectorField("query_vector",
                        "HNSW", {
                            "TYPE": "FLOAT32",
                            "DIM": self.vector_dim,
                            "DISTANCE_METRIC": "COSINE"
                        }
                    )
                )
                definition = IndexDefinition(prefix=["cache:"], index_type=IndexType.HASH)
                self.r.ft(self.index_name).create_index(schema, definition=definition)
                print("🚀 [Semantic Cache] Redis Vector Index 생성 완료.")
            except Exception as create_error:
                # 여기서 에러가 찍힌다면 99% 모듈 미설치 또는 파라미터 불일치입니다.
                print(f"❌ [Semantic Cache] 인덱스 생성 치명적 실패: {create_error}")

    async def get_embedding(self, text: str) -> List[float]:
        # 비동기 임베딩 생성
        return await self.embeddings.aembed_query(text)

    async def search_cache(self, query_text: str) -> Optional[str]:
        print("search_cache!!!!")
        try:
            query_vector = await self.get_embedding(query_text)
            query_vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()

            q = Query("*=>[KNN 1 @query_vector $vec AS score]")\
                .return_fields("response_text", "score")\
                .dialect(2)
            params = {"vec": query_vector_bytes}
            
            # Redis 검색
            res = self.r.ft(self.index_name).search(q, query_params=params)
            
            if res.total > 0:
                top_hit = res.docs[0]
                score = float(top_hit.score)
                print(f'Redis!! score : {score}, self.distance_threshold : {self.distance_threshold}')
                if score < self.distance_threshold:
                    print(f"[Semantic Cache Hit] Score: {score:.4f}")
                    return top_hit.response_text
            
            return None
        except Exception as e:
            print(f"[Cache Search Error] {e}")
            return None

    async def store_cache(self, query_text: str, response_text: str):
        try:
            query_vector = await self.get_embedding(query_text)
            query_vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
            
            key = f"cache:{hash(query_text)}"
            mapping = {
                "response_text": response_text,
                "query_vector": query_vector_bytes,
                "created_at": time.time()
            }
            
            pipe = self.r.pipeline()
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, 86400) # 24시간 TTL
            pipe.execute()
            print(f"[Cache Saved] Query: {query_text[:20]}...")
        except Exception as e:
            print(f"[Cache Store Error] {e}")