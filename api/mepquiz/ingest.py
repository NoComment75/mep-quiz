import json, sys
from pathlib import Path
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Subject, Question, DifficultyEnum

def upsert_question(db, subject_id, difficulty, text, options, correct):
    existing = (
        db.query(Question)
          .filter(
              Question.subject_id == subject_id,
              Question.difficulty == difficulty,  # include difficulty in uniqueness
              Question.text == text
          ).first()
    )
    if existing:
        return False
    from json import dumps
    q = Question(
        subject_id=subject_id,
        difficulty=difficulty,
        text=text,
        options=dumps(options),
        correct_answer=correct,
    )
    db.add(q)
    return True

def main(root: str):
    root_path = Path(root)
    db = SessionLocal()
    created = skipped = 0
    try:
        for subj_dir in root_path.iterdir():
            if not subj_dir.is_dir(): 
                continue
            subject_code = subj_dir.name
            subject = db.query(Subject).filter(Subject.code==subject_code).first()
            if not subject:
                print(f"[WARN] Subject '{subject_code}' not found. Skipping.")
                continue
            for diff_name in ("easy","medium","hard"):
                p = subj_dir / f"{diff_name}.json"
                if not p.exists():
                    continue
                data = json.loads(p.read_text(encoding="utf-8"))
                for item in data:
                    text = item["text"].strip()
                    options = item["options"]
                    correct = item["correct_answer"]
                    if correct not in options:
                        skipped += 1
                        continue
                    ok = upsert_question(db, subject.id, DifficultyEnum(diff_name), text, options, correct)
                    created += 1 if ok else 0
                db.commit()
        print(f"Import complete. Created: {created}, Skipped: {skipped}")
    finally:
        db.close()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/questions"
    main(path)
