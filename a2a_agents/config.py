from pydantic_settings import BaseSettings, SettingsConfigDict


class WrapperSettings(BaseSettings):
    """Where REST services listen; the A2A addresses come from the supervisor's settings."""

    model_config = SettingsConfigDict(env_prefix='A2A_AGENTS_', env_file='.env', extra='ignore')

    group2_reader_url: str = 'http://127.0.0.1:8000'
    group2_connections_url: str = 'http://127.0.0.1:8001'
