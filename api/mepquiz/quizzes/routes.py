from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from .db import Base


class DifficultyEnum(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class AttemptStatusEnum(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    expired = "expired"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    difficulty = Column(Enum(DifficultyEnum), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON string for now
    # widened to Text so long answers import cleanly
    correct_answer = Column(Text, nullable=False)
    challenged = Column(Boolean, default=False)
    challenge_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Prevent duplicates within the same subject + difficulty + text
    __table_args__ = (
        UniqueConstraint("subject_id", "difficulty", "text", name="uq_questions_subject_diff_text"),
    )

    subject = relationship("Subject", backref="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    difficulty = Column(Enum(DifficultyEnum), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=True)

    # New fields for integrity and lifecycle
    question_ids = Column(JSONB, nullable=True)  # list of question IDs served by /start
    status = Column(Enum(AttemptStatusEnum), nullable=False, default=AttemptStatusEnum.in_progress)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")
    subject = relationship("Subject")
    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_attempt_subject_diff_created", "subject_id", "difficulty", "created_at"),
    )


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_once"),
    )
