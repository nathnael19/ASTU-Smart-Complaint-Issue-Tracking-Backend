from typing import Optional
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .enums import ReportFileType, ReportStatus
from .base import UUIDModel, TimestampModel

class ReportBase(BaseModel):
    name: str
    file_type: ReportFileType = ReportFileType.PDF
    category: str
    status: ReportStatus = ReportStatus.GENERATING
    storage_path: Optional[str] = None
    generated_by: Optional[UUID] = None
    department_id: Optional[UUID] = None
    date_range_from: Optional[date] = None
    date_range_to: Optional[date] = None

class ReportCreate(ReportBase):
    pass

class ReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    storage_path: Optional[str] = None

class Report(ReportBase, UUIDModel, TimestampModel):
    model_config = ConfigDict(from_attributes=True)
