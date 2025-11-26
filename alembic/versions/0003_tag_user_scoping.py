"""Add user scoping to tags"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.drop_constraint("tags_slug_key", "tags", type_="unique")
    op.create_unique_constraint("uq_user_tag_name", "tags", ["user_id", "name"])
    op.create_unique_constraint("uq_user_tag_slug", "tags", ["user_id", "slug"])


def downgrade() -> None:
    op.drop_constraint("uq_user_tag_slug", "tags", type_="unique")
    op.drop_constraint("uq_user_tag_name", "tags", type_="unique")
    op.create_unique_constraint("tags_slug_key", "tags", ["slug"])
    op.drop_column("tags", "user_id")
