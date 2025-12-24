import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DB_NAME: str

    # Session and admin settings
    SESSION_SECRET: str = "change-this-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # CORS settings
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    )

    @property
    def get_db_url(self):
        return f"sqlite+aiosqlite:///{self.DB_NAME}"

    @property
    def auth_data(self):
        return {"secret_key": self.SECRET_KEY, "algorithm": self.ALGORITHM}

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
