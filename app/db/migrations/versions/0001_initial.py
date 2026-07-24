from collections.abc import Sequence

from alembic import op

from app.db import schema

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    schema.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    schema.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
