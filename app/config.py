"""Typed runtime settings; credentials are supplied through the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by the API and command-line tools."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    auto_seed: bool = True
    query_timeout: float = 8.0
    data_path: str = "data/processed/supplygraph.json"
    max_concurrent_simulations: int = 2
