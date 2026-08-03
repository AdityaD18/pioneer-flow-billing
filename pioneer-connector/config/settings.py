import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Pioneer Tally Connector"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"
    
    TALLY_HOST: str = "localhost"
    TALLY_PORT: int = 9000
    TALLY_TIMEOUT: int = 30
    TALLY_COMPANY: str = "Pioneer Automation"
    
    CACHE_TTL_SECONDS: int = 300
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
