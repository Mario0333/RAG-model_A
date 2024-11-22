from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int

    FILE_DEFAULT_CHUNK_SIZE: int

    MONGODG_URL: str # Correct usage of ClassVar for class-level variables
    MONGODG_DATABASE: str       # Correctly annotate this as a regular field

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
