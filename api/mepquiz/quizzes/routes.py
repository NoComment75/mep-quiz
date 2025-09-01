from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os, json

from ..deps import get_db
from ..models import (
    Subject,
    Question,
    DifficultyEnum,
    QuizAttempt,
    QuizAnswer,
    AttemptStatusEnum,
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

PER_QUESTION_SECONDS = int(os.getenv("PER_QUESTION_SECONDS", "45"))

# ---------- helpers ----------

def _to_id_set(value) -> set[int]:
    """
    Coerce question_ids (JSONB) that may arrive as a Python list OR as a JSON string
    back into a set[int]. Returns empty set on failure.
    """
    try:
        v = value
        if isinstance(v, str):
            v = json.loads(v)
        if v is None:
            return set()
        return set(int(x) for x in v)
    except Exception:
        return set()

# ---------- Sample (ad-hoc set, no attempt created) ----------

@router.get("/sample")
def sample_quiz(
    subject_code: str,
    difficulty: DifficultyEnum,
    limit: int = Query(25, ge=1, le=50),
    db: Session = Depends(get_db)
):
    subj = db.query(Subject).filter(Subject.code == subject_code).first()
    if not subj:
        raise HTTPException(status_code=400, detail="Unknown subject_code")

    rows = (
        db.query(Question)
        .filter(Question.subject_id == subj.id, Question.difficulty == difficulty)
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    questions = [
        {"id": r.id, "text": r.text, "options": json.loads(r.options or "[]")}
        for r in rows
    ]

    return {
        "subject_code": subject_code,
        "difficulty": difficulty,
        "per_question_seconds": PER_QUESTION_SECONDS,
        "count": len(questions),
        "questions": questions
    }

# ---------- Start (creates an attempt + returns question set) ----------

class StartRequest(BaseModel):
    subject_code: str
    difficulty: DifficultyEnum
    limit: int = 25  # clamped server-side to 1..50

@router.post("/start")
def start_quiz(payload: StartRequest, db: Session = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.code == payload.subject_code).first()
    if not subj:
        raise HTTPException(status_code=400, detail="Unknown subject_code")

    pick = max(1, min(payload.limit, 50))
    rows = (
        db.query(Question)
        .filter(
            Question.subject_id == subj.id,
            Question.difficulty == payload.difficulty
        )
        .order_by(func.random())
        .limit(pick)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="No questions available for that subject/difficulty")

    qids = [r.id for r in rows]

    attempt = QuizAttempt(
        user_id=None,  # wire when auth lands
        subject_id=subj.id,
        difficulty=payload.difficulty,
        total_questions=len(rows),
        correct_count=0,
        duration_seconds=None,
        status=AttemptStatusEnum.in_progress,
        started_at=datetime.utcnow(),
        question_ids=qids,
    )
    db.add(attempt)
    db.flush()  # get attempt.id

    questions = [
        {"id": r.id, "text": r.text, "options": json.loads(r.options or "[]")}
        for r in rows
    ]

    db.commit()

    return {
        "attempt_id": attempt.id,
        "subject_code": payload.subject_code,
        "difficulty": payload.difficulty,
        "per_question_seconds": PER_QUESTION_SECONDS,
        "count": len(questions),
        "questions": questions,
    }

# ---------- Submit results (updates existing attempt if attempt_id provided) ----------

class AnswerIn(BaseModel):
    question_id: int
    selected: str
    time_taken_seconds: Optional[int] = None

class SubmitIn(BaseModel):
    attempt_id: Optional[int] = None  # tie results to an existing attempt from /start (preferred)
    subject_code: str
    difficulty: DifficultyEnum
    answers: List[AnswerIn]

@router.post("/submit")
def submit_quiz(payload: SubmitIn, db: Session = Depends(get_db)):
    # Validate subject
    subj = db.query(Subject).filter(Subject.code == payload.subject_code).first()
    if not subj:
        raise HTTPException(status_code=400, detail="Unknown subject_code")

    qids = [int(a.question_id) for a in payload.answers]
    if not qids:
        raise HTTPException(status_code=400, detail="No answers provided")

    # Fetch and validate questions belong to subject + difficulty
    rows = (
        db.query(Question)
        .filter(
            Question.id.in_(qids),
            Question.subject_id == subj.id,
            Question.difficulty == payload.difficulty
        )
        .all()
    )
    qmap = {r.id: r for r in rows}
    if len(qmap) != len(qids):
        bad = sorted(set(qids) - set(qmap))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid question ids for {payload.subject_code}/{payload.difficulty}: {bad}"
        )

    # Create or load attempt
    if payload.attempt_id is not None:
        attempt = db.query(QuizAttempt).filter(QuizAttempt.id == payload.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="attempt_id not found")
        if attempt.subject_id != subj.id or attempt.difficulty != payload.difficulty:
            raise HTTPException(status_code=400, detail="attempt_id does not match subject/difficulty")

        # Ensure the submitted questions match what /start provided
        start_set = _to_id_set(attempt.question_ids)
        if not start_set:
            raise HTTPException(status_code=400, detail="attempt has no stored question set")
        if set(qids) != start_set:
            raise HTTPException(
                status_code=400,
                detail="Submitted question_ids do not match the started attempt's question set"
            )

        # Clear previous answers (idempotent resubmits)
        db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).delete(synchronize_session=False)
        total_questions = attempt.total_questions
    else:
        # Submit-only flow: build a self-contained attempt using provided qids
        attempt = QuizAttempt(
            user_id=None,
            subject_id=subj.id,
            difficulty=payload.difficulty,
            total_questions=len(qids),
            correct_count=0,
            duration_seconds=None,
            status=AttemptStatusEnum.in_progress,
            started_at=datetime.utcnow(),
            question_ids=qids,
        )
        db.add(attempt)
        db.flush()
        total_questions = attempt.total_questions

    correct = 0
    duration = 0

    # Record answers
    for a in payload.answers:
        q = qmap[a.question_id]
        is_corr = (a.selected == q.correct_answer)
        if a.time_taken_seconds:
            duration += int(a.time_taken_seconds)
        if is_corr:
            correct += 1

        db.add(QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected=a.selected,
            is_correct=is_corr,
            time_taken_seconds=a.time_taken_seconds
        ))

    # Finalise and commit
    attempt.correct_count = correct
    attempt.duration_seconds = duration or None
    attempt.completed_at = datetime.utcnow()
    attempt.status = AttemptStatusEnum.completed

    db.commit()

    return {
        "attempt_id": attempt.id,
        "subject_code": payload.subject_code,
        "difficulty": payload.difficulty,
        "total_questions": total_questions,
        "correct_count": correct,
        "percent": round(100 * correct / total_questions, 1) if total_questions else 0.0,
        "duration_seconds": attempt.duration_seconds,
    }

# ---------- Attempt detail ----------

@router.get("/attempt/{attempt_id}")
def get_attempt(attempt_id: int, db: Session = Depends(get_db)):
    attempt = (
        db.query(QuizAttempt, Subject.code.label("subject_code"))
        .join(Subject, Subject.id == QuizAttempt.subject_id)
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="attempt not found")

    a, subject_code = attempt
    answers = (
        db.query(QuizAnswer, Question)
        .join(Question, Question.id == QuizAnswer.question_id)
        .filter(QuizAnswer.attempt_id == a.id)
        .order_by(QuizAnswer.id.asc())
        .all()
    )

    items = []
    for ans, q in answers:
        items.append({
            "question_id": q.id,
            "text": q.text,
            "selected": ans.selected,
            "correct_answer": q.correct_answer,
            "is_correct": ans.is_correct,
            "time_taken_seconds": ans.time_taken_seconds,
        })

    percent = round(100 * (a.correct_count or 0) / (a.total_questions or 1), 1) if a.total_questions else 0.0

    return {
        "attempt_id": a.id,
        "subject_code": subject_code,
        "difficulty": a.difficulty,
        "status": a.status,
        "total_questions": a.total_questions,
        "correct_count": a.correct_count,
        "percent": percent,
        "duration_seconds": a.duration_seconds,
        "question_ids": list(_to_id_set(a.question_ids)),
        "started_at": a.started_at,
        "completed_at": a.completed_at,
        "answers": items,
    }

# ---------- Attempt list (NEW) ----------

@router.get("/attempts")
def list_attempts(
    subject_code: Optional[str] = None,
    difficulty: Optional[DifficultyEnum] = None,
    status: Optional[AttemptStatusEnum] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    subj = None
    if subject_code:
        subj = db.query(Subject).filter(Subject.code == subject_code).first()
        if not subj:
            raise HTTPException(status_code=400, detail="Unknown subject_code")

    q = (
        db.query(QuizAttempt, Subject.code.label("subject_code"))
        .join(Subject, Subject.id == QuizAttempt.subject_id)
    )
    if subj:
        q = q.filter(QuizAttempt.subject_id == subj.id)
    if difficulty:
        q = q.filter(QuizAttempt.difficulty == difficulty)
    if status:
        q = q.filter(QuizAttempt.status == status)

    rows = (
        q.order_by(QuizAttempt.id.desc())
         .limit(limit)
         .all()
    )

    out = []
    for a, sub_code in rows:
        percent = round(100 * (a.correct_count or 0) / (a.total_questions or 1), 1) if a.total_questions else 0.0
        out.append({
            "attempt_id": a.id,
            "subject_code": sub_code,
            "difficulty": a.difficulty,
            "status": a.status,
            "total_questions": a.total_questions,
            "correct_count": a.correct_count,
            "percent": percent,
            "duration_seconds": a.duration_seconds,
            "started_at": a.started_at,
            "completed_at": a.completed_at,
        })

    return {"count": len(out), "attempts": out}
