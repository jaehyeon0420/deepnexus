# 비동기 엔진과 비동기 세션 생성
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
# Redis 비동기 클라이언트 생성
import redis.asyncio as redis
# .env 설정값 불러오기
from app.core.config import settings

# 1. PostgreSQL 엔진 생성
# echo=True : 개발 중 쿼리 로그 확인용 (배포 시 False)
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 2. 세션 팩토리 생성
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. FastAPI 의존성 주입용 함수
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # 요청 처리 성공 시 커밋은 서비스 레이어에서 commit()을 호출하므로 여기선 생략
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()