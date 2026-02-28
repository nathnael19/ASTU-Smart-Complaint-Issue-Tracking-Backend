from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .base import UUIDModel

class NotificationBase(BaseModel):
    user_id: UUID
    title: str
    message: str
    type: str
    link: Optional[str] = None
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class Notification(NotificationBase, UUIDModel):
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
