from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .base import UUIDModel, TimestampModel, SoftDeleteModel

class InternalNoteBase(BaseModel):
    complaint_id: UUID
    author_id: UUID
    content: str
    is_highlighted: bool = False

class InternalNoteCreate(InternalNoteBase):
    pass

class InternalNoteUpdate(BaseModel):
    content: Optional[str] = None
    is_highlighted: Optional[bool] = None

class InternalNote(InternalNoteBase, UUIDModel, TimestampModel, SoftDeleteModel):
    model_config = ConfigDict(from_attributes=True)
