# app/services/memory.py
import json

class ConversationMemoryManager:
    def __init__(self, redis_client, window_size=10):
        self.r = redis_client
        self.window_size = window_size  # 버퍼 사이즈 설정 (최근 N개 메시지)
        self.prefix = "history:"

    async def get_history(self, session_id: str):
        # Redis에서 최근 N개의 대화 내역 가져오기
        key = f"{self.prefix}{session_id}"
        history_data = self.r.lrange(key, 0, self.window_size - 1)
        # JSON 문자열을 리스트로 변환하여 반환
        return [json.loads(h) for h in reversed(history_data)]

    async def add_message(self, session_id: str, role: str, content: str):
        key = f"{self.prefix}{session_id}"
        message = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        
        pipe = self.r.pipeline()
        pipe.lpush(key, message) # 앞에 삽입
        pipe.ltrim(key, 0, self.window_size - 1) # 버퍼 사이즈 초과분 삭제
        pipe.expire(key, 604800) # 일주일 TTL 설정
        pipe.execute()