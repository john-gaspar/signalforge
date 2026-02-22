from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    project_name: str = Field("signalforge", env="SIGNALFORGE_PROJECT_NAME")
    version: str = Field("0.1.0", env="SIGNALFORGE_VERSION")
    api_prefix: str = Field("/api", env="SIGNALFORGE_API_PREFIX")
    database_url: str = Field(
        "sqlite:///./artifacts/runs/db.sqlite3", env="SIGNALFORGE_DATABASE_URL"
    )
    environment: str = Field("local", env="SIGNALFORGE_ENV")
    port: int = Field(8000, env="PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
