from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str = 'Voice Navigator Backend'
    host: str = '0.0.0.0'
    port: int = 8000
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    top_k: int = 4
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'

    base_dir: Path = Path(__file__).resolve().parent.parent
    raw_data_dir: Path = base_dir / 'data' / 'raw'
    processed_data_dir: Path = base_dir / 'data' / 'processed'


settings = Settings()
