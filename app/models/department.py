from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .base import UUIDModel, TimestampModel

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Department(DepartmentBase, UUIDModel, TimestampModel):
    model_config = ConfigDict(from_attributes=True)
