from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=list[schemas.PromptOut])
def list_prompts(db: Session = Depends(get_db)):
    return db.query(models.Prompt).order_by(models.Prompt.id.desc()).all()


@router.post("", response_model=schemas.PromptOut, status_code=201)
def create_prompt(payload: schemas.PromptCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Prompt).filter(models.Prompt.name == payload.name).count()
    prompt = models.Prompt(name=payload.name, version=existing + 1, system_text=payload.system_text)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.get("/{prompt_id}", response_model=schemas.PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(models.Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(404, "Prompt not found")
    return prompt


@router.put("/{prompt_id}", response_model=schemas.PromptOut)
def update_prompt(prompt_id: int, payload: schemas.PromptUpdate, db: Session = Depends(get_db)):
    prompt = db.get(models.Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(404, "Prompt not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(prompt, key, value)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(models.Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(404, "Prompt not found")
    db.delete(prompt)
    db.commit()
