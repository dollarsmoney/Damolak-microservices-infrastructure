"""
Data Service Configuration
"""
import os


class Settings:
    APP_NAME: str = "damolak-data-service"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Inter-service URLs
    PROCESSING_SERVICE_URL: str = os.getenv(
        "PROCESSING_SERVICE_URL", "http://processing-service:8081"
    )
    NOTIFICATION_SERVICE_URL: str = os.getenv(
        "NOTIFICATION_SERVICE_URL", "http://notification-service:5000"
    )


settings = Settings()
