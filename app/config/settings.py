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

    mongodb_connection_collection: str = "prospect_connections"

    # NestJS
    nestjs_base_url: str = "http://localhost:3000"
    prospect_processing_api_key: str

    #RabitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_scoring_queue: str = "prospect-scoring" 

    #Cloudnary Configuration 
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "realgrowth/conversations"
    mongodb_conversation_collection: str = "prospect_conversations"


    huggingface_api_token: str
    huggingface_ocr_model: str = "Qwen/Qwen2.5-VL-3B-Instruct"
    huggingface_provider: str = "featherless-ai"

    groq_api_key: str
    groq_ocr_model: str = "qwen/qwen3.8-27b"
    groq_llm_model: str = "openai/gpt-oss-120b"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()