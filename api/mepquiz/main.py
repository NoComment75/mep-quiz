from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MEP Quiz API", version="0.0.1")

# CORS
allow_origin = os.getenv("ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allow_origin] if allow_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
@app.get("/api/health")
def health():
    return {"ok": True}

# Routers
# Subjects/questions endpoints (list questions, subjects, sample etc.)
try:
    from .questions.routes import router as questions_router
    app.include_router(questions_router)
except Exception:
    pass

# Quiz endpoints (/api/quiz/sample, /api/quiz/submit)
try:
    from .quizzes.routes import router as quiz_router
    app.include_router(quiz_router)
except Exception:
    pass
