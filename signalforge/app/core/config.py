from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    artifacts_dir: str = "/code/artifacts"
    rq_queue_name: str = "signalforge"

    class Config:
        env_prefix = ""
        case_sensitive = False

settings = Settings()