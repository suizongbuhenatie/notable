from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models import Note, NoteContent, NoteTag, Tag


router = APIRouter(prefix="/notes", tags=["notes"])


class NoteBase(BaseModel):
    title: str
    slug: str
    type: str
    parent_id: UUID | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: UUID | None = None


class NoteCreate(NoteBase):
    tags: List[str] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[UUID | None] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    user_id: Optional[UUID | None] = None


class MoveRequest(BaseModel):
    parent_id: UUID | None = None
    order: Optional[int] = None


class NoteRead(BaseModel):
    id: UUID
    user_id: UUID | None
    title: str
    slug: str
    parent_id: UUID | None
    order_index: int
    metadata: Dict[str, Any]
    type: str
    tags: List[str]
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteTreeItem(NoteRead):
    children: List["NoteTreeItem"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


NoteTreeItem.model_rebuild()


class NotesListResponse(BaseModel):
    total: int
    items: List[NoteRead]

    model_config = {"from_attributes": True}


class NoteContentCreate(BaseModel):
    tiptap_json: Dict[str, Any]
    markdown: Optional[str] = None


class NoteContentRead(BaseModel):
    version: int
    tiptap_json: Dict[str, Any] | None
    markdown: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = {"from_attributes": True}


def _serialize_note(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "user_id": note.user_id,
        "title": note.title,
        "slug": note.slug,
        "parent_id": note.parent_id,
        "order_index": note.order_index,
        "metadata": note.metadata or {},
        "type": note.type,
        "tags": [nt.tag.slug for nt in note.note_tags],
        "updated_at": note.updated_at,
        "created_at": note.created_at,
    }


def _apply_filters(
    stmt,
    *,
    title: str | None,
    tag: str | None,
    note_type: str | None,
    user_id: UUID | None,
):
    if user_id:
        stmt = stmt.where(Note.user_id == user_id)
    if title:
        stmt = stmt.where(Note.title.ilike(f"%{title}%"))
    if note_type:
        stmt = stmt.where(Note.type == note_type)
    if tag:
        stmt = stmt.join(Note.note_tags).join(NoteTag.tag)
        if user_id:
            stmt = stmt.where(Tag.user_id == user_id)
        stmt = stmt.where(Tag.slug == tag)
    return stmt


def _convert_tiptap_to_markdown(content: dict[str, Any]) -> str:
    def render_inline(node: dict[str, Any]) -> str:
        text = node.get("text", "")
        for mark in node.get("marks", []) or []:
            mark_type = mark.get("type")
            if mark_type == "bold":
                text = f"**{text}**"
            elif mark_type == "italic":
                text = f"*{text}*"
            elif mark_type == "strike":
                text = f"~~{text}~~"
            elif mark_type == "code":
                text = f"`{text}`"
            elif mark_type == "link":
                href = mark.get("attrs", {}).get("href", "")
                text = f"[{text}]({href})" if href else text
        return text

    def render_node(node: dict[str, Any]) -> str:
        node_type = node.get("type")
        children = node.get("content", []) or []

        if node_type == "doc":
            return "\n\n".join(filter(None, (render_node(child) for child in children)))
        if node_type == "paragraph":
            return "".join(render_node(child) for child in children)
        if node_type == "text":
            return render_inline(node)
        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            level = min(max(level, 1), 6)
            return f"{'#' * level} {''.join(render_node(child) for child in children)}"
        if node_type == "bulletList":
            return "\n".join(f"- {render_node(child).strip()}" for child in children)
        if node_type == "orderedList":
            start = node.get("attrs", {}).get("start", 1)
            lines: list[str] = []
            for index, child in enumerate(children, start=start):
                lines.append(f"{index}. {render_node(child).strip()}")
            return "\n".join(lines)
        if node_type == "listItem":
            return " ".join(render_node(child).strip() for child in children)
        if node_type == "blockquote":
            return "\n".join(f"> {render_node(child).strip()}" for child in children)
        if node_type == "codeBlock":
            language = node.get("attrs", {}).get("language") or ""
            code_content = "".join(render_node(child) for child in children)
            fence = f"```{language}" if language else "```"
            return f"{fence}\n{code_content}\n```"
        if node_type == "horizontalRule":
            return "---"
        return " ".join(render_node(child) for child in children)

    return render_node(content).strip()


def _serialize_content(content: NoteContent) -> dict[str, Any]:
    return {
        "version": content.version,
        "tiptap_json": content.tiptap_json,
        "markdown": content.markdown,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
        "deleted_at": content.deleted_at,
    }


def _fetch_note(db: Session, note_id: UUID) -> Note:
    note = (
        db.execute(
            select(Note)
            .options(joinedload(Note.note_tags).joinedload(NoteTag.tag))
            .where(Note.id == note_id)
        )
        .scalars()
        .first()
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def _fetch_tag(db: Session, tag_id: UUID) -> Tag:
    tag = db.execute(select(Tag).where(Tag.id == tag_id)).scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


def _set_note_tags(db: Session, note: Note, tag_slugs: list[str]) -> None:
    normalized = {slug.strip() for slug in tag_slugs if slug.strip()}
    current = {note_tag.tag.slug: note_tag for note_tag in note.note_tags}

    for slug in set(current) - normalized:
        note.note_tags.remove(current[slug])

    for slug in normalized - set(current):
        tag = db.execute(
            select(Tag).where(Tag.slug == slug, Tag.user_id == note.user_id)
        ).scalar_one_or_none()
        if not tag:
            tag = Tag(name=slug, slug=slug, user_id=note.user_id)
            db.add(tag)
            db.flush([tag])
        note.note_tags.append(NoteTag(tag=tag))


def _assert_not_descendant(db: Session, note: Note, new_parent_id: UUID | None) -> None:
    if not new_parent_id:
        return

    current_parent = (
        db.execute(select(Note).where(Note.id == new_parent_id)).scalars().first()
    )
    while current_parent:
        if current_parent.id == note.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move a note into its own descendant",
            )
        current_parent = current_parent.parent


def _reorder_siblings(
    db: Session, note: Note, parent_id: UUID | None, position: Optional[int]
) -> None:
    siblings = (
        db.execute(
            select(Note)
            .where(Note.parent_id == parent_id, Note.id != note.id)
            .order_by(Note.order_index, Note.created_at)
        )
        .scalars()
        .all()
    )

    if position is None or position > len(siblings):
        position = len(siblings)
    position = max(position, 0)

    siblings.insert(position, note)

    for index, sibling in enumerate(siblings):
        sibling.order_index = index


def _assert_same_scope(note: Note, tag: Tag) -> None:
    if tag.user_id and note.user_id != tag.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag belongs to a different user",
        )


def _fetch_content(db: Session, note_id: UUID, version: int) -> NoteContent:
    content = (
        db.execute(
            select(NoteContent).where(
                NoteContent.note_id == note_id, NoteContent.version == version
            )
        )
        .scalars()
        .first()
    )
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return content


@router.get("", response_model=NotesListResponse)
def list_notes(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    title: str | None = None,
    tag: str | None = None,
    note_type: str | None = Query(default=None, alias="type"),
    user_id: UUID | None = None,
):
    base_stmt = select(Note)
    filtered_stmt = _apply_filters(
        base_stmt, title=title, tag=tag, note_type=note_type, user_id=user_id
    )

    total_query = _apply_filters(
        select(func.count(func.distinct(Note.id))).select_from(Note),
        title=title,
        tag=tag,
        note_type=note_type,
        user_id=user_id,
    )
    total = db.execute(total_query).scalar_one()

    if tag:
        filtered_stmt = filtered_stmt.distinct(Note.id)

    notes = (
        db.execute(
            filtered_stmt.options(joinedload(Note.note_tags).joinedload(NoteTag.tag))
            .order_by(Note.order_index, Note.created_at)
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    return {"total": total, "items": [_serialize_note(note) for note in notes]}


@router.get("/tree", response_model=List[NoteTreeItem])
def get_notes_tree(
    *,
    db: Session = Depends(get_db),
    title: str | None = None,
    tag: str | None = None,
    note_type: str | None = Query(default=None, alias="type"),
    user_id: UUID | None = None,
):
    stmt = _apply_filters(
        select(Note), title=title, tag=tag, note_type=note_type, user_id=user_id
    )
    if tag:
        stmt = stmt.distinct(Note.id)

    notes = (
        db.execute(
            stmt.options(joinedload(Note.note_tags).joinedload(NoteTag.tag)).order_by(
                Note.order_index, Note.created_at
            )
        )
        .scalars()
        .all()
    )

    tree: dict[UUID, dict[str, Any]] = {note.id: {**_serialize_note(note), "children": []} for note in notes}
    roots: list[dict[str, Any]] = []

    for note in notes:
        node = tree[note.id]
        if note.parent_id and note.parent_id in tree:
            tree[note.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(*, db: Session = Depends(get_db), payload: NoteCreate):
    if payload.parent_id:
        _fetch_note(db, payload.parent_id)

    max_order = db.execute(
        select(func.coalesce(func.max(Note.order_index), -1)).where(Note.parent_id == payload.parent_id)
    ).scalar_one()
    note = Note(
        user_id=payload.user_id,
        title=payload.title,
        slug=payload.slug,
        type=payload.type,
        parent_id=payload.parent_id,
        metadata=payload.metadata,
        order_index=max_order + 1,
    )
    db.add(note)
    db.flush([note])

    if payload.tags:
        _set_note_tags(db, note, payload.tags)

    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(_serialize_note(note))


@router.get("/{note_id}", response_model=NoteRead)
def read_note(note_id: UUID, db: Session = Depends(get_db)):
    note = _fetch_note(db, note_id)
    return NoteRead.model_validate(_serialize_note(note))


@router.put("/{note_id}", response_model=NoteRead)
def update_note(note_id: UUID, *, db: Session = Depends(get_db), payload: NoteUpdate):
    note = _fetch_note(db, note_id)

    if payload.parent_id is not None and payload.parent_id != note.parent_id:
        _fetch_note(db, payload.parent_id) if payload.parent_id else None
        _assert_not_descendant(db, note, payload.parent_id)
        note.parent_id = payload.parent_id
        _reorder_siblings(db, note, payload.parent_id, None)

    if payload.title is not None:
        note.title = payload.title
    if payload.slug is not None:
        note.slug = payload.slug
    if payload.type is not None:
        note.type = payload.type
    if payload.metadata is not None:
        note.metadata = payload.metadata
    if payload.user_id is not None and payload.user_id != note.user_id:
        note.user_id = payload.user_id
        note.note_tags = [
            nt
            for nt in note.note_tags
            if nt.tag.user_id is None or nt.tag.user_id == note.user_id
        ]

    if payload.tags is not None:
        _set_note_tags(db, note, payload.tags)

    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(_serialize_note(note))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, db: Session = Depends(get_db)) -> None:
    note = _fetch_note(db, note_id)
    db.delete(note)
    db.commit()
    return None


@router.post("/{note_id}/tags/{tag_id}", response_model=NoteRead)
def attach_tag(note_id: UUID, tag_id: UUID, db: Session = Depends(get_db)):
    note = _fetch_note(db, note_id)
    tag = _fetch_tag(db, tag_id)
    _assert_same_scope(note, tag)

    existing = next((nt for nt in note.note_tags if nt.tag_id == tag.id), None)
    if not existing:
        note.note_tags.append(NoteTag(tag=tag))
        db.commit()
        db.refresh(note)

    return NoteRead.model_validate(_serialize_note(note))


@router.delete("/{note_id}/tags/{tag_id}", status_code=status.HTTP_200_OK, response_model=NoteRead)
def detach_tag(note_id: UUID, tag_id: UUID, db: Session = Depends(get_db)):
    note = _fetch_note(db, note_id)
    tag = _fetch_tag(db, tag_id)
    _assert_same_scope(note, tag)

    note.note_tags = [nt for nt in note.note_tags if nt.tag_id != tag.id]
    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(_serialize_note(note))


@router.post("/{note_id}/move", response_model=NoteRead)
def move_note(note_id: UUID, *, db: Session = Depends(get_db), payload: MoveRequest):
    note = _fetch_note(db, note_id)
    if payload.parent_id:
        _fetch_note(db, payload.parent_id)
    _assert_not_descendant(db, note, payload.parent_id)

    note.parent_id = payload.parent_id
    _reorder_siblings(db, note, payload.parent_id, payload.order)

    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(_serialize_note(note))


@router.get("/{note_id}/content", response_model=NoteContentRead)
def get_latest_content(
    note_id: UUID,
    *,
    db: Session = Depends(get_db),
    include_deleted: bool = False,
):
    _fetch_note(db, note_id)
    stmt = select(NoteContent).where(NoteContent.note_id == note_id)
    if not include_deleted:
        stmt = stmt.where(NoteContent.deleted_at.is_(None))
    content = db.execute(stmt.order_by(NoteContent.version.desc())).scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No content found for note"
        )
    return NoteContentRead.model_validate(_serialize_content(content))


@router.get("/{note_id}/content/history", response_model=List[NoteContentRead])
def get_content_history(
    note_id: UUID,
    *,
    db: Session = Depends(get_db),
    include_deleted: bool = False,
):
    _fetch_note(db, note_id)
    stmt = select(NoteContent).where(NoteContent.note_id == note_id)
    if not include_deleted:
        stmt = stmt.where(NoteContent.deleted_at.is_(None))
    contents = db.execute(stmt.order_by(NoteContent.version.desc())).scalars().all()
    return [NoteContentRead.model_validate(_serialize_content(content)) for content in contents]


@router.post("/{note_id}/content", response_model=NoteContentRead, status_code=status.HTTP_201_CREATED)
def save_content(note_id: UUID, *, db: Session = Depends(get_db), payload: NoteContentCreate):
    _fetch_note(db, note_id)
    max_version = db.execute(
        select(func.coalesce(func.max(NoteContent.version), 0)).where(
            NoteContent.note_id == note_id
        )
    ).scalar_one()
    next_version = max_version + 1

    markdown = payload.markdown or _convert_tiptap_to_markdown(payload.tiptap_json)

    content = NoteContent(
        note_id=note_id,
        version=next_version,
        tiptap_json=payload.tiptap_json,
        markdown=markdown,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return NoteContentRead.model_validate(_serialize_content(content))


@router.delete("/{note_id}/content/{version}", response_model=NoteContentRead)
def soft_delete_content(note_id: UUID, version: int, db: Session = Depends(get_db)):
    _fetch_note(db, note_id)
    content = _fetch_content(db, note_id, version)
    content.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(content)
    return NoteContentRead.model_validate(_serialize_content(content))


@router.post("/{note_id}/content/{version}/restore", response_model=NoteContentRead)
def restore_content(note_id: UUID, version: int, db: Session = Depends(get_db)):
    _fetch_note(db, note_id)
    content = _fetch_content(db, note_id, version)
    content.deleted_at = None
    db.commit()
    db.refresh(content)
    return NoteContentRead.model_validate(_serialize_content(content))
