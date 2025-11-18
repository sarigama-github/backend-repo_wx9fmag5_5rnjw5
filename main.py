import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Docy AI Documentation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocPage(BaseModel):
    slug: str
    title: str
    summary: Optional[str] = None
    content: str


# Simple in-memory docs content for the MVP (no persistence needed for static docs)
DOC_PAGES: List[DocPage] = [
    DocPage(
        slug="getting-started",
        title="Getting Started",
        summary="Quick intro to Docy AI Documentation site.",
        content=(
            "# Getting Started\n\n"
            "Welcome to Docy AI Documentation. This site showcases a clean docs experience "
            "with a built-in AI helper. Use the sidebar to browse topics or ask the AI a question.\n\n"
            "- Navigate through topics\n- Use the search to find content\n- Open the chat bubble to ask anything about the docs\n"
        ),
    ),
    DocPage(
        slug="writing-docs",
        title="Writing Docs",
        summary="Structure and style guidelines.",
        content=(
            "# Writing Docs\n\n"
            "Keep content concise, add headings, and prefer examples.\n\n"
            "## Tips\n- One idea per section\n- Use bullet points\n- Provide code where helpful\n"
        ),
    ),
    DocPage(
        slug="faq",
        title="FAQ",
        summary="Common questions and answers.",
        content=(
            "# FAQ\n\n"
            "**What is Docy AI?**\n\n"
            "A friendly documentation experience with an AI helper to guide readers.\n\n"
            "**Does it need a database?**\n\n"
            "For static docs, no. For user content or analytics, yes.\n"
        ),
    ),
]


@app.get("/")
def read_root():
    return {"message": "Docy AI Backend is running"}


@app.get("/api/pages", response_model=List[DocPage])
def list_pages():
    return DOC_PAGES


@app.get("/api/pages/{slug}", response_model=DocPage)
def get_page(slug: str):
    for p in DOC_PAGES:
        if p.slug == slug:
            return p
    raise HTTPException(status_code=404, detail="Page not found")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: List[str] = []


@app.post("/api/ask", response_model=AskResponse)
def ask_ai(req: AskRequest):
    q = req.question.strip().lower()
    # Extremely simple rule-based helper that references our docs
    if not q:
        return AskResponse(answer="Please provide a question.")

    # Try to find relevant page by keyword
    matches = []
    for p in DOC_PAGES:
        hay = f"{p.title} {p.summary or ''} {p.content}".lower()
        if any(k in hay for k in q.split() if len(k) > 3):
            matches.append(p)

    if matches:
        tips = "\n".join([f"- {m.title} (/docs/{m.slug})" for m in matches[:3]])
        answer = (
            "Here are some details I found in the documentation that may help:\n\n"
            f"{tips}\n\n"
            "Open one of these pages for a deeper dive."
        )
        return AskResponse(answer=answer, sources=[f"/docs/{m.slug}" for m in matches[:3]])

    # Default fallback
    return AskResponse(
        answer=(
            "I couldn't find an exact match in the docs. Try rephrasing your question "
            "or browse the sections from the sidebar."
        )
    )


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db  # type: ignore
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:  # pragma: no cover
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
