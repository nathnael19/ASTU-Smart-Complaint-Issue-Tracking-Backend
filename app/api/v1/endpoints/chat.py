"""
AI Chatbot endpoint for students.
Uses OpenRouter (free tier) when OPENROUTER_API_KEY is set; otherwise returns a helpful fallback.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.dependencies import get_current_user_profile

router = APIRouter()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are a helpful assistant for Adama Science and Technology University (ASTU) students using the ASTU Smart Complaint & Issue Tracking system. Your role is to help students with:

- Submitting complaints: how to file a complaint, what information to include, categories (Facility & Maintenance, Academic Affairs, IT & Network, Student Services), and attaching files or images.
- Tracking complaints: how to check status (Open, In Progress, Resolved), view complaint history, and when to expect updates.
- General campus issues: dormitory maintenance, lab equipment, internet connectivity, classroom facilities, registrar, library, and academic affairs—direct them to submit a complaint in the appropriate category when relevant.
- Password reset: use "Forgot Password" on the login page; they will receive an email with a reset link.
- Course registration: typically opens two weeks before the semester; add/drop in the first two weeks. Specific dates are in the academic calendar.
- Transcripts: request via registrar's office portal or in person; processing takes 3–5 business days.
- Dormitory maintenance: submit under Facilities category; for emergencies they can contact campus facilities hotline at 9812.

Be concise, friendly, and accurate. If you are not sure about something specific (e.g. exact dates or internal procedures), suggest they check the Knowledge Base or contact the relevant office. Do not make up phone numbers or URLs beyond what is stated here."""

# Fallback FAQ-style answers when OpenAI is not configured
FALLBACK_ANSWERS = [
    ("how do i submit", "Go to Submit New Complaint from the sidebar. Enter a title, choose a category (e.g. Facility & Maintenance, IT & Network), add a description, and you can attach files or images. Click Submit when done."),
    ("how do i track", "Open My Complaints from the sidebar to see all your complaints and their status: Open, In Progress, or Resolved. Click a complaint to see full details and any staff notes."),
    ("forgot password", "On the login page, click Forgot Password and enter your ASTU email. You will receive a reset link by email. Check spam if you don't see it."),
    ("categories", "Complaint categories include: Facility & Maintenance (dorms, cafeteria, maintenance), Academic Affairs, IT & Network (Wi‑Fi, portal, email), and Student Services. Choose the one that best fits your issue."),
    ("attachment", "When submitting a complaint you can attach files or images (e.g. photos of the problem). Use the upload area on the form; you can add up to 5 files."),
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
    """Simple keyword matching over FAQ for when OpenAI is not available."""
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
    """Student-facing chatbot. Requires authentication. Uses OpenAI if configured, else fallback."""
    # Only students can use the chatbot (optional: restrict to STUDENT role)
    if profile.get("role") not in ("STUDENT", "STAFF", "ADMIN"):
        raise HTTPException(status_code=403, detail="Chat is available for authenticated users.")

    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if settings.OPENROUTER_API_KEY:
        try:
            import openai
            client = openai.OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=settings.OPENROUTER_API_KEY,
            )
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if payload.history:
                for m in payload.history[-10:]:  # last 10 turns
                    if m.role in ("user", "assistant") and m.content:
                        messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": message})
            response = client.chat.completions.create(
                model=settings.OPENROUTER_MODEL or "google/gemma-2-9b-it:free",
                messages=messages,
                max_tokens=500,
                temperature=0.5,
            )
            reply = (response.choices[0].message.content or "").strip()
            if not reply:
                reply = _fallback_reply(message)
            return ChatResponse(reply=reply, source="openrouter")
        except Exception:
            # On API error, fall back to keyword reply
            reply = _fallback_reply(message)
            return ChatResponse(reply=reply, source="fallback")

    reply = _fallback_reply(message)
    return ChatResponse(reply=reply, source="fallback")
