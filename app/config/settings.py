from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RealGrowth Data Service"
    app_env: str = "development"
    port: int = 8000
    apollo_api_key: str
    clay_api_key: str
    google_maps_api_key: str

    mongodb_uri: str
    mongodb_database: str
    mongodb_prospect_collection: str = "prospects"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()