from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Booking Architecture Stand"
    database_url: str = "sqlite:///./stand.db"
    worker_delay_ms: int = Field(default=0, ge=0)


settings = Settings()
