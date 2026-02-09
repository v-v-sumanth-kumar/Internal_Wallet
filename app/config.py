from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    DATABASE_URL: str = "postgresql+asyncpg://internal_wallet_user:LUAYEhFKk0ZY5CCWKCAUS9aL2G6sYeN6@dpg-d6420ichg0os73csc5hg-a.oregon-postgres.render.com/internal_wallet"
    APP_NAME: str = "Internal Wallet Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    SYSTEM_TREASURY_ID: int = 1
    SYSTEM_BONUS_POOL_ID: int = 2
    SYSTEM_REVENUE_ID: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
