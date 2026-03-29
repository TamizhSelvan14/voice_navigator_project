import itertools
import threading
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Module-level round-robin state (shared across all Settings instances)
_api_keys_cycle = None
_api_keys_lock = threading.Lock()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / '.env'),
        env_file_encoding='utf-8',
    )

    app_name: str = 'Voice Navigator Backend'
    host: str = '0.0.0.0'
    port: int = 8000

    # NVIDIA NIM API – 4 keys for round-robin rotation
    nvidia_api_key: str = ''
    nvidia_api_key_2: str = ''
    nvidia_api_key_3: str = ''
    nvidia_api_key_4: str = ''

    def next_api_key(self) -> str:
        """Return the next API key in round-robin order (thread-safe)."""
        global _api_keys_cycle
        with _api_keys_lock:
            if _api_keys_cycle is None:
                keys = [k for k in [self.nvidia_api_key, self.nvidia_api_key_2, self.nvidia_api_key_3, self.nvidia_api_key_4] if k]
                _api_keys_cycle = itertools.cycle(keys)
            return next(_api_keys_cycle)
    nvidia_base_url: str = 'https://integrate.api.nvidia.com/v1'
    nvidia_parse_url: str = 'https://integrate.api.nvidia.com/v1/chat/completions'
    embedding_model: str = 'nvidia/llama-nemotron-embed-vl-1b-v2'
    reranker_model: str = 'nvidia/llama-nemotron-rerank-1b-v2'
    llm_model: str = 'nvidia/nemotron-3-super-120b-a12b'
    parse_model: str = 'nvidia/nemotron-parse'

    # RAG tuning
    top_k: int = 8
    rerank_top_k: int = 4
    embedding_batch_size: int = 50

    base_dir: Path = Path(__file__).resolve().parent.parent
    raw_data_dir: Path = base_dir / 'data' / 'raw'
    processed_data_dir: Path = base_dir / 'data' / 'processed'
    assets_dir: Path = base_dir / 'data' / 'assets'


settings = Settings()
