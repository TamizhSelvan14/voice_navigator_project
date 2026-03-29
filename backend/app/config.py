from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str = 'Voice Navigator Backend'
    host: str = '0.0.0.0'
    port: int = 8000

    # NVIDIA NIM API
    nvidia_api_key: str = ''
    nvidia_base_url: str = 'https://integrate.api.nvidia.com/v1'
    embedding_model: str = 'nvidia/llama-nemotron-embed-1b-v2'
    reranker_model: str = 'nvidia/llama-nemotron-rerank-1b-v2'
    llm_model: str = 'nvidia/nemotron-3-super-120b-a12b'

    # RAG tuning
    top_k: int = 8
    rerank_top_k: int = 4
    embedding_batch_size: int = 50

    base_dir: Path = Path(__file__).resolve().parent.parent
    raw_data_dir: Path = base_dir / 'data' / 'raw'
    processed_data_dir: Path = base_dir / 'data' / 'processed'


settings = Settings()
