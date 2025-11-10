"""add image transform fields to section item"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240618_135700"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("section_item", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("image_scale", sa.Float(), nullable=False, server_default="1.0")
        )
        batch_op.add_column(
            sa.Column("image_rotation", sa.Float(), nullable=False, server_default="0.0")
        )


def downgrade():
    with op.batch_alter_table("section_item", schema=None) as batch_op:
        batch_op.drop_column("image_rotation")
        batch_op.drop_column("image_scale")
