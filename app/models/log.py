from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .enums import LogEntryType
from .base import UUIDModel

class CommunicationLogBase(BaseModel):
    complaint_id: UUID
    actor_id: Optional[UUID] = None
    entry_type: LogEntryType
    message: str
    metadata: Optional[dict[str, Any]] = None

class CommunicationLogCreate(CommunicationLogBase):
    pass

class CommunicationLog(CommunicationLogBase, UUIDModel):
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
