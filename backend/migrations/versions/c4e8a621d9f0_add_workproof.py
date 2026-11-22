"""add WorkProof portable reputation records"""
from alembic import op
import sqlalchemy as sa
revision="c4e8a621d9f0"; down_revision="b1b1313604cd"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("workproof_profiles",sa.Column("artisan_id",sa.String(36),sa.ForeignKey("artisan_profiles.id"),nullable=False),sa.Column("score",sa.Integer(),nullable=False,server_default="0"),sa.Column("verified_jobs",sa.Integer(),nullable=False,server_default="0"),sa.Column("external_verified_jobs",sa.Integer(),nullable=False,server_default="0"),sa.Column("repeat_clients",sa.Integer(),nullable=False,server_default="0"),sa.Column("completion_rate",sa.Numeric(5,2),nullable=False,server_default="0"),sa.Column("average_rating",sa.Numeric(3,2)),sa.Column("unresolved_disputes",sa.Integer(),nullable=False,server_default="0"),sa.Column("years_verified",sa.Numeric(5,2),nullable=False,server_default="0"),sa.Column("last_calculated_at",sa.DateTime(timezone=True)),sa.Column("id",sa.String(36),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("artisan_id"))
    op.create_index("ix_workproof_profiles_artisan_id","workproof_profiles",["artisan_id"],unique=True)
    op.create_table("workproof_evidence",sa.Column("artisan_id",sa.String(36),sa.ForeignKey("artisan_profiles.id"),nullable=False),sa.Column("evidence_type",sa.String(40),nullable=False),sa.Column("title",sa.String(180),nullable=False),sa.Column("description",sa.Text()),sa.Column("occurred_at",sa.DateTime(timezone=True)),sa.Column("verifier_name",sa.String(160),nullable=False),sa.Column("verifier_contact",sa.String(254),nullable=False),sa.Column("verification_method",sa.String(40)),sa.Column("status",sa.String(20),nullable=False,server_default="pending"),sa.Column("reviewer_id",sa.String(36),sa.ForeignKey("users.id")),sa.Column("decision_reason",sa.String(500)),sa.Column("decided_at",sa.DateTime(timezone=True)),sa.Column("public_metadata",sa.JSON(),nullable=False),sa.Column("id",sa.String(36),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_workproof_evidence_artisan_id","workproof_evidence",["artisan_id"]);op.create_index("ix_workproof_evidence_status","workproof_evidence",["status"])

def downgrade():
    op.drop_table("workproof_evidence");op.drop_table("workproof_profiles")
