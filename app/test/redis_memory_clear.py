
"""
[위험/주의] 모든 사용자의 대화 히스토리를 일괄 삭제합니다.
"""
import redis
import os

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=False)
window_size = 30
prefix = "history:"
        
        
# history:* 패턴에 매칭되는 모든 키를 찾습니다.
keys = redis_client.keys(f"{prefix}*")
print('memory keys : ', keys)
if keys:
    # 찾은 키들을 한 번에 삭제합니다.
    redis_client.delete(*keys)
    print(f"🔥 [Memory Clear] {len(keys)}개의 대화 기록이 삭제되었습니다.")



    
"""
특정 사용자의 대화 히스토리만 삭제합니다.

key = f"{self.prefix}{session_id}"
self.r.delete(key)
print(f"🧹 [Memory Clear] 사용자 {session_id}의 기록이 삭제되었습니다.")
"""        
