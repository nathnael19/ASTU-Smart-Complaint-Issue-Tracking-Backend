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

SYSTEM_PROMPT = """You are a helpful assistant for Adama Science and Technology University (ASTU) students. Your role is to help students with:

- Submitting complaints: how to file a complaint, what information to include, categories (Facility & Maintenance, Academic Affairs, IT & Network, Student Services, Library, Financial), and attaching files.
- Tracking complaints: how to check status (Open, In Progress, Resolved), view history, and expected updates.
- General campus issues: dormitory maintenance, lab equipment, internet, library (borrowing, digital resources), and financial (fees, clearing).
- Password reset: Use "Forgot Password" on the login page; check email for the reset link.
- Course registration: Typically opens two weeks before the semester; add/drop in the first two weeks.
- Transcripts: Request via registrar's office portal or in person; takes 3–5 business days.
- Dormitory maintenance: Submit under Facilities; for emergencies contact campus hotline at 9812.
- Library Services: Borrowing books, digital resource access, and study space booking.
- Financial Affairs: Tuition payments, scholarship status, and financial clearance procedures.

Be concise, friendly, and accurate. If unsure, suggest checking the Knowledge Base or contacting the relevant office."""

# Fallback FAQ-style answers when OpenRouter is not configured
FALLBACK_ANSWERS = [
    ("how do i submit", "Go to Submit New Complaint from the sidebar. Enter a title, choose a category (e.g. Facility & Maintenance, IT & Network), add a description, and you can attach files or images. Click Submit when done."),
    ("how do i track", "Open My Complaints from the sidebar to see all your complaints and their status: Open, In Progress, or Resolved. Click a complaint to see full details and any staff notes."),
    ("forgot password", "On the login page, click Forgot Password and enter your ASTU email. You will receive a reset link by email. Check spam if you don't see it."),
    ("categories", "Complaint categories include: Facility & Maintenance, Academic Affairs, IT & Network, Student Services, Library, and Financial. Choose the one that best fits your issue."),
    ("attachment", "When submitting a complaint you can attach files or images. Use the upload area on the form; you can add up to 5 files."),
    ("status", "Complaints can be Open (new), In Progress (being worked on), or Resolved. You can see the status in My Complaints and on the complaint detail page."),
    ("dormitory", "For dormitory or maintenance issues, submit a complaint under the Facility & Maintenance category. For emergencies, contact the campus facilities hotline at 9812."),
    ("transcript", "You can request an official transcript through the registrar's office portal or in person. Processing usually takes 3–5 business days."),
    ("registration", "Course registration typically opens two weeks before the start of each semester. The add/drop period is the first two weeks of classes. Check the academic calendar for exact dates."),
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

    if settings.OPENROUTER_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
