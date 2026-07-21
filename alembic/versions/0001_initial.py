"""Initial schema.

Revision ID: 0001
"""

from collections.abc import Sequence

from alembic import op
from app.database import models  # noqa: F401
from app.database.base import Base

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
