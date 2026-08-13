from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GeoAI Flood Prediction API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    app_version: str = "0.1.0"
    weather_provider_enabled: bool = True
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_cache_ttl_seconds: int = 600
    maubin_forecast_latitude: float = 16.712
    maubin_forecast_longitude: float = 95.643
    mqtt_enabled: bool = False
    mqtt_broker_host: str = "127.0.0.1"
    mqtt_broker_port: int = 1883
    mqtt_topic: str = "floodguard/stations/+/readings"
    mqtt_qos: int = 1
    mqtt_client_id: str = "floodguard-backend"
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls_enabled: bool = False
    mqtt_keepalive_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        return value

    @field_validator("mqtt_qos")
    @classmethod
    def validate_mqtt_qos(cls, value: int) -> int:
        if value not in (0, 1, 2):
            raise ValueError("MQTT_QOS must be 0, 1, or 2")
        return value

    @field_validator("mqtt_broker_port")
    @classmethod
    def validate_mqtt_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("MQTT_BROKER_PORT must be between 1 and 65535")
        return value

    @field_validator("mqtt_keepalive_seconds")
    @classmethod
    def validate_mqtt_keepalive(cls, value: int) -> int:
        if value < 5 or value > 3600:
            raise ValueError(
                "MQTT_KEEPALIVE_SECONDS must be between 5 and 3600"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
