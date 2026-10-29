from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RealGrowth Data Service"
    app_env: str = "development"
    port: int = 8000

    # Provider API keys
    apollo_api_key: str
    clay_api_key: str
    google_maps_api_key: str

    # MongoDB
    mongodb_uri: str
    mongodb_database: str
    mongodb_prospect_collection: str = "prospects"

    # NestJS
    nestjs_base_url: str = "http://localhost:3000"
    prospect_processing_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()