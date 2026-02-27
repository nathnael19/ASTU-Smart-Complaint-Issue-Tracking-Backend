from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class UUIDModel(BaseModel):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)

class TimestampModel(BaseModel):
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SoftDeleteModel(BaseModel):
    deleted_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)
