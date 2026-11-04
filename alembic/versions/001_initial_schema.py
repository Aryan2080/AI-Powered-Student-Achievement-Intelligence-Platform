"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-04 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('email', sa.String(length=255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Students table
    op.create_table(
        'students',
        sa.Column('student_id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('department', sa.String(length=128), nullable=False),
        sa.Column('program', sa.String(length=64), nullable=False),
        sa.Column('year_of_study', sa.Integer(), nullable=False),
        sa.Column('gpa', sa.Float(), nullable=False),
        sa.Column('declared_skills', sa.Text(), nullable=False),
        sa.Column('declared_interests', sa.Text(), nullable=False),
        sa.Column('career_goals', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Faculty table
    op.create_table(
        'faculty',
        sa.Column('faculty_id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('department', sa.String(length=128), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('permissions', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Opportunities table
    op.create_table(
        'opportunities',
        sa.Column('opportunity_id', sa.String(length=64), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('opportunity_type', sa.String(length=32), nullable=False),
        sa.Column('organization', sa.String(length=255), nullable=False),
        sa.Column('eligible_departments', sa.Text(), nullable=False),
        sa.Column('eligible_years', sa.String(length=64), nullable=False),
        sa.Column('eligible_degree', sa.String(length=128), nullable=False),
        sa.Column('min_gpa', sa.Float(), nullable=False),
        sa.Column('required_skills', sa.Text(), nullable=False),
        sa.Column('preferred_skills', sa.Text(), nullable=False),
        sa.Column('domain_tags', sa.String(length=255), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('reward_or_stipend', sa.String(length=128), nullable=True),
        sa.Column('location_type', sa.String(length=32), nullable=False),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('external_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('source_name', sa.String(length=128), nullable=False),
        sa.Column('text_hash', sa.String(length=64), nullable=True),
        sa.Column('embedding_version', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_opportunities_title', 'opportunities', ['title'])
    op.create_index('ix_opportunities_type', 'opportunities', ['opportunity_type'])

    # Achievements table
    op.create_table(
        'achievements',
        sa.Column('achievement_id', sa.String(length=64), primary_key=True),
        sa.Column('student_id', sa.String(length=64), sa.ForeignKey('students.student_id'), nullable=False),
        sa.Column('source_achievement_id', sa.String(length=64), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('domain_tags', sa.String(length=255), nullable=False),
        sa.Column('skills', sa.Text(), nullable=False),
        sa.Column('level', sa.String(length=32), nullable=False),
        sa.Column('achievement_date', sa.Date(), nullable=True),
        sa.Column('evidence_status', sa.String(length=32), nullable=False),
        sa.Column('evidence_url', sa.String(length=512), nullable=True),
        sa.Column('verification_remarks', sa.Text(), nullable=True),
        sa.Column('verified_by_faculty_id', sa.String(length=64), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=False),
        sa.Column('classifier_confidence', sa.Float(), nullable=False),
        sa.Column('source_pipeline_version', sa.String(length=32), nullable=False),
        sa.Column('classifier_model_version', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('student_id', 'source_achievement_id', name='uq_student_source_achievement'),
    )

    # Saved Opportunities table
    op.create_table(
        'saved_opportunities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('student_id', sa.String(length=64), sa.ForeignKey('students.student_id'), nullable=False),
        sa.Column('opportunity_id', sa.String(length=64), sa.ForeignKey('opportunities.opportunity_id'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('student_id', 'opportunity_id', name='uq_student_opportunity'),
    )

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('notification_id', sa.String(length=64), primary_key=True),
        sa.Column('student_id', sa.String(length=64), sa.ForeignKey('students.student_id'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=32), nullable=False),
        sa.Column('dedupe_key', sa.String(length=128), unique=True, nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('saved_opportunities')
    op.drop_table('achievements')
    op.drop_table('opportunities')
    op.drop_table('faculty')
    op.drop_table('students')
    op.drop_table('users')
