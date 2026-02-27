import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the project root to sys.path to allow importing 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.models import (
        User, UserCreate, UserRole, UserStatus,
        Complaint, ComplaintStatus, ComplaintPriority, ComplaintCategory,
        Department, DepartmentCreate
    )
    print("✅ Successfully imported models from app.models")
    
    # Test User model
    user_data = {
        "id": uuid4(),
        "first_name": "Test",
        "last_name": "User",
        "email": "test@astu.edu.et",
        "role": UserRole.STUDENT,
        "status": UserStatus.ACTIVE,
        "full_name": "Test User",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    user = User(**user_data)
    print(f"✅ User model validated: {user.full_name}")

    # Test Complaint model
    complaint_data = {
        "id": uuid4(),
        "ticket_number": "ASTU-1234",
        "title": "Test Complaint",
        "description": "This is a test complaint description.",
        "category": ComplaintCategory.IT_AND_NETWORK,
        "priority": ComplaintPriority.MEDIUM,
        "status": ComplaintStatus.OPEN,
        "submitted_by": uuid4(),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    complaint = Complaint(**complaint_data)
    print(f"✅ Complaint model validated: {complaint.ticket_number}")

    # Test Department model
    dept_data = {
        "id": uuid4(),
        "name": "Software Engineering",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    dept = Department(**dept_data)
    print(f"✅ Department model validated: {dept.name}")

except Exception as e:
    print(f"❌ Verification failed: {e}")
    sys.exit(1)
