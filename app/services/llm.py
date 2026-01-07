from langchain_openai import AzureChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings # 변경된 import
from app.core.config import settings

def get_llm(model_name: str = "gpt-4o"):
    # 매개변수에 따라, Open AI 모델 다르게 생성하여 리턴
    deployment = settings.AZURE_DEPLOYMENT_GPT4O if model_name == "gpt-4o" else settings.AZURE_DEPLOYMENT_GPT4O_MINI
    return AzureChatOpenAI(
        azure_deployment=deployment,
        openai_api_version=settings.AZURE_OPENAI_API_VERSION,
        temperature=0,
        streaming=True # 토큰별 실시간 응답을 위함
    )

def get_embeddings():
    model_kwargs = {'device': settings.EMBEDDING_DEVICE}
    encode_kwargs = {'normalize_embeddings': True} # 코사인 유사도 검색 시 정규화 권장

    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )