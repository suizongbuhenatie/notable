from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError

from app.dependencies import SessionLocal
from app.models import Asset, Note, NoteContent, NoteTag, Setting, Tag, User

logger = logging.getLogger(__name__)


def seed() -> None:
    """Populate the database with starter data."""

    db = SessionLocal()
    try:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.flush()

        root_note = Note(
            user_id=user.id,
            title="Welcome to Notable",
            slug="welcome-to-notable",
            type="page",
            metadata={"pinned": True},
        )
        db.add(root_note)
        db.flush()

        db.add(
            NoteContent(
                note_id=root_note.id,
                version=1,
                tiptap_json={"type": "doc", "content": []},
                markdown="# Welcome to Notable\nStart writing your notes!",
            )
        )

        tag = Tag(name="welcome", slug="welcome")
        db.add(tag)
        db.flush()

        db.add(NoteTag(note_id=root_note.id, tag_id=tag.id))

        db.add(
            Asset(
                note_id=root_note.id,
                s3_key="uploads/example.txt",
                mime="text/plain",
                size=34,
            )
        )

        db.add_all(
            [
                Setting(key="app.theme", value={"mode": "dark"}),
                Setting(user_id=user.id, key="profile.language", value="en"),
            ]
        )

        db.commit()
        logger.info("Database seeded successfully")
    except IntegrityError:
        db.rollback()
        logger.info("Seed data already present; skipping.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
