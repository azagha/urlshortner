from datetime import date, timezone
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

class UserResponse(BaseModel):
    message: str

class UrlCreate(BaseModel):
    original_url: str
    expires_at: date | None = Field(default=None, examples=[None])

    @field_validator("expires_at")
    @classmethod
    def validate_future_date(cls, v: date | None) -> date | None:
            if v is not None and v <= date.today():
                raise ValueError("Expiration date must be in the future")
            return v

class UrlResponse(BaseModel):
    original_url: str
    shortened_url: str
    expires_at: date

class UserAdminStats(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    total_links: int
    total_clicks: int

class AdminDashboardResponse(BaseModel):
    total_platform_links: int
    users: list[UserAdminStats]