"""
AI Chatbot endpoint for students.
Uses OpenRouter (free tier) when OPENROUTER_API_KEY is set; otherwise returns a helpful fallback.
"""
import httpx
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.dependencies import get_current_user_profile

router = APIRouter()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are a highly intelligent and friendly AI assistant for Adama Science and Technology University (ASTU) students. Your primary mission is to provide accurate, helpful, and empathetic guidance.

### Your Knowledge Areas:
1.  **Complaint Submission**: Explain how to use the "Submit New Complaint" form. Essential categories:
    *   **Facility & Maintenance**: For dorm issues, cafeteria, or campus safety.
    *   **Academic Affairs**: Grading, course issues, or registration.
    *   **IT & Network**: Internet access, portal logins, and labs.
    *   **Student Services**: Services related to student life.
    *   **Library**: Borrowing, resources, and study spaces.
    *   **Financial**: Fees, payments, and clearance.
2.  **Complaint Tracking**: Explain statuses:
    *   **Open**: New ticket, awaiting staff review.
    *   **In Progress**: A staff member is actively working on it.
    *   **Resolved**: Issue is fixed! Resolving sets a timestamp and notifies the student.
    *   **Closed**: Finalized ticket.
3.  **Emergency Contacts**: 
    *   Campus Security: **9811**
    *   Facilities Hotline: **9812**
4.  **Academic Calendar**: Registration typically starts 2 weeks before the semester; add/drop is the first 2 weeks.
5.  **Transcripts**: Request at Registrar's Office; takes 3-5 business days.

### Your Persona:
- Be concise but thorough.
- Use a friendly tone.
- If you don't know an answer, suggest checking the **Knowledge Base** in the sidebar.
- **You are NOT authorized to change data**, only to guide.

### User Context:
When communicating, remember you are speaking to an authenticated ASTU student. Use their name and ID if provided in the context preamble."""

# Fallback FAQ-style answers with more detail
FALLBACK_ANSWERS = [
    ("how do i submit", "Go to **Submit New Complaint** from the sidebar. Enter a title, choose a category (e.g., Facility & Maintenance, IT & Network), add a description, and you can attach up to 5 files or images. Click Submit when done."),
    ("how do i track", "Visit **My Complaints** from the sidebar to see your tickets. Statuses include: **Open** (new), **In Progress** (active), and **Resolved** (fixed). Click any ticket to see details or chat with staff."),
    ("forgot password", "On the login page, click **Forgot Password** and enter your ASTU email. You will receive a reset link. Check your spam folder if you don't see it within 5 minutes."),
    ("categories", "Categories include: Facility & Maintenance, Academic Affairs, IT & Network, Student Services, Library, and Financial. Choose the one that best fits your issue."),
    ("attachment", "You can add up to 5 attachments (images/docs) when submitting a complaint using the upload area on the form."),
    ("status", "Tickets progress from **Open** → **In Progress** → **Resolved**. You can check this anytime in the 'My Complaints' section."),
    ("dormitory", "For maintenance or dorm issues, use the **Facility & Maintenance** category. For emergencies, call the facilities hotline at **9812**."),
    ("transcript", "Official transcripts are requested through the registrar's office portal or in person. It typically takes **3–5 business days**."),
    ("registration", "Course registration normally opens two weeks before the semester. The add/drop period is the first two weeks of classes. Check the academic calendar for specific dates."),
    ("security", "For urgent security matters or emergencies, please contact the campus security hotline at **9811**."),
    ("library", "Under the **Library** category, you can report issues with borrowing, digital resources, or study spaces."),
    ("financial", "For tuition, scholarships, or clearance questions, use the **Financial** category."),
]


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    reply: str
    source: str  # "openrouter" | "fallback"


def _fallback_reply(user_message: str) -> str:
    """Simple keyword matching over FAQ for when OpenRouter is not available."""
    lower = user_message.lower().strip()
    for keyword_phrase, answer in FALLBACK_ANSWERS:
        if keyword_phrase in lower:
            return answer
    return (
        "I can help with questions about submitting and tracking complaints at ASTU. "
        "Try asking: how to submit a complaint, how to track my status, or about categories and attachments. "
        "You can also open **Knowledge Base** from the sidebar for more guides and FAQs."
    )


@router.post("/", response_model=ChatResponse, summary="Send a message to the AI assistant")
async def chat(
    payload: ChatRequest,
    profile: dict = Depends(get_current_user_profile),
):
    """Student-facing chatbot. Requires authentication. Uses OpenRouter if configured, else fallback."""
    if profile.get("role") not in ("STUDENT", "STAFF", "ADMIN"):
        raise HTTPException(status_code=403, detail="Chat is available for authenticated users.")

    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Injected Context for Personalization
    full_name = profile.get("full_name") or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "Student"
    id_num = profile.get("student_id_number") or profile.get("id") or "N/A"
    context_preamble = f"[Context: You are currently assisting {full_name} (ID: {id_num}). Acknowledge them if helpful, but prioritize their question.]"

    if settings.OPENROUTER_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.append({"role": "system", "content": context_preamble})
            
            if payload.history:
                for m in payload.history[-10:]:
                    if m.role in ("user", "assistant") and m.content:
                        messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": message})

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://astu-smart-complaint-issue-tracking.netlify.app",
                        "X-Title": "ASTU Smart Complaint & Issue Tracking",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL or "google/gemma-2-9b-it:free",
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.5,
                    },
                    timeout=30.0
                )
                
            if response.status_code == 200:
                data = response.json()
                reply = data["choices"][0]["message"]["content"].strip()
                if reply:
                    return ChatResponse(reply=reply, source="openrouter")
            
            # If API fails or returns error, use fallback
            print(f"OpenRouter Request Failed: Status {response.status_code}, Body: {response.text}")
            reply = _fallback_reply(message)
            return ChatResponse(reply=reply, source="fallback")
        except Exception as e:
            import traceback
            print(f"OpenRouter Exception: {str(e)}")
            traceback.print_exc()
            reply = _fallback_reply(message)
            return ChatResponse(reply=reply, source="fallback")

    reply = _fallback_reply(message)
    return ChatResponse(reply=reply, source="fallback")
