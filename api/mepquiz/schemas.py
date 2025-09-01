from pydantic import BaseModel, Field, constr
from typing import List
from .models import DifficultyEnum

class SubjectOut(BaseModel):
    id: int
    code: str
    name: str
    class Config: from_attributes = True

class SubjectCreate(BaseModel):
    code: constr(strip_whitespace=True)
    name: constr(strip_whitespace=True)

class QuestionCreate(BaseModel):
    subject_code: constr(strip_whitespace=True)
    difficulty: DifficultyEnum
    text: constr(strip_whitespace=True)
    options: List[str] = Field(min_length=2)
    correct_answer: str

class QuestionOut(BaseModel):
    id: int
    subject_id: int
    difficulty: DifficultyEnum
    text: str
    options: List[str]
    correct_answer: str
    class Config: from_attributes = True
