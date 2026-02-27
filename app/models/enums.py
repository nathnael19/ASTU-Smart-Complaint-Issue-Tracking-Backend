from enum import Enum

class UserRole(str, Enum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    ADMIN = "ADMIN"

class UserStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"

class ComplaintStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class ComplaintPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ComplaintCategory(str, Enum):
    IT_AND_NETWORK = "IT_AND_NETWORK"
    FACILITY_AND_MAINTENANCE = "FACILITY_AND_MAINTENANCE"
    ACADEMIC_AFFAIRS = "ACADEMIC_AFFAIRS"
    STUDENT_SERVICES = "STUDENT_SERVICES"
    REGISTRAR_OFFICE = "REGISTRAR_OFFICE"
    ACADEMIC_RESOURCES = "ACADEMIC_RESOURCES"
    OTHER = "OTHER"

class LogEntryType(str, Enum):
    STATUS_CHANGE = "STATUS_CHANGE"
    ASSIGNMENT = "ASSIGNMENT"
    COMMENT = "COMMENT"
    ESCALATION = "ESCALATION"
    RESOLUTION = "RESOLUTION"
    EMAIL_SENT = "EMAIL_SENT"
    SMS_SENT = "SMS_SENT"

class ReportFileType(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"

class ReportStatus(str, Enum):
    GENERATING = "Generating"
    READY = "Ready"
    FAILED = "Failed"
