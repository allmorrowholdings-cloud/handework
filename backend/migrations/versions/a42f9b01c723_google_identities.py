"""Add stable Google subject identity mapping."""
from alembic import op
import sqlalchemy as sa

revision = 'a42f9b01c723'
down_revision = 'e6c27f91a842'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('google_identities',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('google_sub', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('google_sub', name='uq_google_subject'))


def downgrade():
    op.drop_table('google_identities')
