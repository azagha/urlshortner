from datetime import datetime
from pydantic import BaseModel

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

class UserResponse(BaseModel):
    message: str

class UrlCreate(BaseModel):
    original_url: str

class UrlResponse(BaseModel):
    original_url: str
    shortened_url: str


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