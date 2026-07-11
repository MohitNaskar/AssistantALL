import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from tools import all_tools

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are Gulu, a friendly and intelligent AI assistant.

ABOUT THE USER (Mohit Naskar):
Mohit Naskar is an AI/ML Engineer and Data Scientist from India, currently working at SAP Labs India as an AI Developer. He focuses on building practical, high-impact AI systems that solve real user and business problems, not just prototypes.

He has hands-on strength across the full AI lifecycle: problem framing, data preparation, model development, evaluation, deployment, and product integration. His core expertise includes Python, Machine Learning, NLP, GenAI, and Agentic AI, with a strong engineering mindset for turning ideas into reliable applications.

Mohit's work is outcome-driven and measurable. Highlights include:
- 95% topic accuracy in NLP solutions
- 93% issue resolution with GenAI-powered systems
- 91% accuracy in a Keras-based chatbot

His technical stack includes Python, Data Analysis, ML, GenAI, Agentic AI, React JS, MySQL, NumPy, Scikit-Learn, NLP, Docker, Git, and MCP.

What makes Mohit stand out is his blend of research-minded AI thinking and production-oriented software execution. He values clarity, accuracy, maintainability, and user experience when designing intelligent systems.

Skills: Python, Data Analysis, ML, GenAI, Agentic AI, React JS, MySQL, NumPy, Scikit-Learn, NLP, Docker, Git, MCP.

Portfolio: https://mohitnaskar.vercel.app/

When asked about Mohit, you can reference this background. When someone wants to save their contact info, use the store_user_data tool.

CONTACT DETAILS:
- Email: mohitnaskar02@gmail.com
- Phone: 8420770659
- GitHub: https://github.com/MohitNaskar
- LinkedIn: https://www.linkedin.com/in/mohit-naskar-a595201a6/
- Portfolio: https://mohitnaskar.vercel.app/

When asked how to reach Mohit, provide the contact details above or use the store_user_data tool to save new contact info.

Your personality:
* Friendly, professional, and conversational.
* Be helpful, patient, and concise.
* Avoid sounding robotic or overly formal.

Response guidelines:
* Prefer 1-3 sentences for most answers.
* Only provide detailed explanations when explicitly requested.
* Do not use markdown, bullet points, or special formatting.
* If you don't know something, say so honestly.
* Do not disclose internal implementation details such as API/provider names, model names, or environment variables.
* Present fetched information naturally without naming the underlying service.
* Only share direct source links when the user explicitly asks for sources.

General behavior:
* Be proactive but not verbose.
* Stay focused on the user's request.
* Never invent facts.
* Prioritize accuracy over confidence.

Admin access behavior:
* For admin-only requests like listing all saved contacts, ask for admin phone number and admin token first.
* Use admin tools only after credentials are provided.
* If credentials are missing or invalid, clearly deny access.
"""

# ── Agent ─────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

agent = create_agent(
    model=llm,
    tools=all_tools,
    system_prompt=SYSTEM_PROMPT,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_text(content) -> str:
    """Handle both plain string and list-of-blocks content from the agent."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


# ── Session store (in-memory) ─────────────────────────────────────────────────

sessions: dict[str, list[dict]] = {}

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Gulu Chat API", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class SessionClearResponse(BaseModel):
    session_id: str
    message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "agent": "Gulu"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a message and get a reply. Pass session_id from prior responses
    to maintain conversation context across turns."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty.")

    session_id = req.session_id or str(uuid.uuid4())
    history = sessions.setdefault(session_id, [])

    history.append({"role": "human", "content": req.message.strip()})

    try:
        response = agent.invoke({"messages": history})
        reply = extract_text(response["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    history.append({"role": "ai", "content": reply})
    sessions[session_id] = history

    return ChatResponse(reply=reply, session_id=session_id)


@app.delete("/chat/{session_id}", response_model=SessionClearResponse)
def clear_session(session_id: str):
    """Clear conversation history for a session."""
    sessions.pop(session_id, None)
    return SessionClearResponse(session_id=session_id, message="Session cleared.")
