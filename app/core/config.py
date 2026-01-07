from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_DEPLOYMENT_GPT4O: str
    AZURE_DEPLOYMENT_GPT4O_MINI: str
    
    # 로컬 경로 혹은 HuggingFace Hub ID 입력
    EMBEDDING_MODEL_NAME: str
    # 모델 실행 디바이스 (cuda:0, mps, cpu 등)
    EMBEDDING_DEVICE: str

    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # langsmith
    LANGSMITH_API_KEY : str
    LANGSMITH_TRACING : bool = True
    LANGSMITH_ENDPOINT : str
    LANGSMITH_PROJECT : str
    
    # JWT 시크릿 키
    SECRET_KEY : str
    
    # Email (SMTP) 설정
    SMTP_SERVER: str = "smtp.naver.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    
    class Config:
        env_file = ".env"

settings = Settings()