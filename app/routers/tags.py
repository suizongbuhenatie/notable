from __future__ import annotations

import re
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models import Note, NoteTag, Tag
from app.routers.notes import NoteRead, _serialize_note


router = APIRouter(prefix="/tags", tags=["tags"])


class TagBase(BaseModel):
    name: str
    slug: str | None = None


class TagCreate(TagBase):
    user_id: UUID


class TagUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class TagRead(BaseModel):
    id: UUID
    user_id: UUID | None
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    total: int
    items: List[TagRead]


_slug_pattern = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    cleaned = _slug_pattern.sub("-", value.lower()).strip("-")
    return cleaned or value


def _fetch_tag(db: Session, tag_id: UUID) -> Tag:
    tag = db.execute(select(Tag).where(Tag.id == tag_id)).scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


@router.get("", response_model=TagListResponse)
def list_tags(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID | None = None,
):
    base_query = select(Tag)
    total_query = select(func.count()).select_from(Tag)
    if user_id:
        base_query = base_query.where(Tag.user_id == user_id)
        total_query = total_query.where(Tag.user_id == user_id)

    total = db.execute(total_query).scalar_one()

    tags = (
        db.execute(
            base_query.order_by(Tag.name).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return {"total": total, "items": tags}


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(*, db: Session = Depends(get_db), payload: TagCreate):
    slug = _slugify(payload.slug or payload.name)
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid slug")

    existing = db.execute(
        select(Tag).where(
            Tag.user_id == payload.user_id,
            (Tag.name == payload.name) | (Tag.slug == slug),
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")

    tag = Tag(user_id=payload.user_id, name=payload.name, slug=slug)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.get("/{tag_id}", response_model=TagRead)
def read_tag(tag_id: UUID, db: Session = Depends(get_db)):
    return _fetch_tag(db, tag_id)


@router.put("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: UUID, *, db: Session = Depends(get_db), payload: TagUpdate):
    tag = _fetch_tag(db, tag_id)

    new_name = payload.name or tag.name
    new_slug = _slugify(payload.slug) if payload.slug is not None else tag.slug
    if not new_slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid slug")

    conflict = db.execute(
        select(Tag).where(
            Tag.id != tag_id,
            Tag.user_id == tag.user_id,
            (Tag.name == new_name) | (Tag.slug == new_slug),
        )
    ).scalar_one_or_none()
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")

    tag.name = new_name
    tag.slug = new_slug

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: UUID, db: Session = Depends(get_db)) -> None:
    tag = _fetch_tag(db, tag_id)
    db.delete(tag)
    db.commit()
    return None


@router.get("/{tag_id}/notes", response_model=List[NoteRead])
def list_notes_by_tag(tag_id: UUID, db: Session = Depends(get_db)):
    tag = _fetch_tag(db, tag_id)

    notes = (
        db.execute(
            select(Note)
            .join(Note.note_tags)
            .options(joinedload(Note.note_tags).joinedload(NoteTag.tag))
            .where(NoteTag.tag_id == tag.id)
            .order_by(Note.order_index, Note.created_at)
        )
        .scalars()
        .all()
    )
    return [NoteRead.model_validate(_serialize_note(note)) for note in notes]
