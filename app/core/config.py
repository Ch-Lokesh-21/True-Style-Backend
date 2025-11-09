from pydantic_settings import BaseSettings
from pydantic import EmailStr
class Settings(BaseSettings):
    PROJECT_NAME: str 
    API_V1_PREFIX: str 
    MONGO_URI: str 
    MONGO_DB : str
    REDIS_HOST : str
    PERM_CACHE_TTL_SECONDS: int
    GRIDFS_BUCKET: str
    POSTGRESQL_URI: str
    BACKEND_BASE_URL: str
    UPLOAD_MAX_BYTES: int
    UPLOAD_ALLOWED_TYPES: str
    
    JWT_ACCESS_TOKEN_SECRET: str
    JWT_REFRESH_TOKEN_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
    MAIL_USERNAME: EmailStr
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str 
    MAIL_SERVER: str 
    MAIL_PORT: int 
    MAIL_STARTTLS: bool = True      
    MAIL_SSL_TLS: bool = False      
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    REFRESH_COOKIE_NAME: str 
    REFRESH_COOKIE_PATH: str 
    REFRESH_COOKIE_SECURE: bool 
    REFRESH_COOKIE_SAMESITE: str 
    REFRESH_COOKIE_MAX_AGE_DAYS: int 
    TOKEN_HASH_PEPPER: str 
    BACKUP_BASE_PATH: str
    CARD_ENC_KEY: str
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

settings = Settings()