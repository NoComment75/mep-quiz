from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from ..deps import get_db
from ..models import Subject, Question, DifficultyEnum
from ..schemas import QuestionCreate, QuestionOut

router = APIRouter(prefix="/api/questions", tags=["questions"])

@router.post("", response_model=QuestionOut)
def add_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.code == payload.subject_code).first()
    if not subj:
        raise HTTPException(status_code=400, detail="Unknown subject_code")
    if payload.correct_answer not in payload.options:
        raise HTTPException(status_code=400, detail="correct_answer must be in options")

    q = Question(
        subject_id=subj.id,
        difficulty=payload.difficulty,
        text=payload.text,
        options=json.dumps(payload.options),
        correct_answer=payload.correct_answer,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return QuestionOut.model_validate({
        "id": q.id,
        "subject_id": q.subject_id,
        "difficulty": q.difficulty,
        "text": q.text,
        "options": json.loads(q.options or "[]"),
        "correct_answer": q.correct_answer
    })

@router.get("", response_model=List[QuestionOut])
def list_questions(
    subject_code: Optional[str] = None,
    difficulty: Optional[DifficultyEnum] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Question)
    if subject_code:
        subj = db.query(Subject).filter(Subject.code == subject_code).first()
        if not subj:
            return []
        q = q.filter(Question.subject_id == subj.id)
    if difficulty:
        q = q.filter(Question.difficulty == difficulty)
    rows = q.order_by(Question.id.desc()).limit(limit).all()
    out: List[QuestionOut] = []
    for row in rows:
        out.append(QuestionOut.model_validate({
            "id": row.id,
            "subject_id": row.subject_id,
            "difficulty": row.difficulty,
            "text": row.text,
            "options": json.loads(row.options or "[]"),
            "correct_answer": row.correct_answer
        }))
    return out
