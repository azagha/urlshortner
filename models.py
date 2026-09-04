from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str



class UrlCreate(BaseModel):
    original_url: str


class UrlResponse(BaseModel):
    url_id: int
    original_url: str
    shortened_url: str
    click_count: int
    last_opened: Optional[datetime] = None
    created_at: datetime
    user_id: Optional[int] = None