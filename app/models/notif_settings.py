from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .base import UUIDModel, TimestampModel

class UserNotificationSettingsBase(BaseModel):
    user_id: UUID
    email_alerts_enabled: bool = True
    sms_alerts_enabled: bool = False
    notify_new_ticket: bool = True
    notify_status_change: bool = True
    notify_high_priority_only: bool = False

class UserNotificationSettingsCreate(UserNotificationSettingsBase):
    pass

class UserNotificationSettingsUpdate(BaseModel):
    email_alerts_enabled: Optional[bool] = None
    sms_alerts_enabled: Optional[bool] = None
    notify_new_ticket: Optional[bool] = None
    notify_status_change: Optional[bool] = None
    notify_high_priority_only: Optional[bool] = None

class UserNotificationSettings(UserNotificationSettingsBase, UUIDModel, TimestampModel):
    model_config = ConfigDict(from_attributes=True)
