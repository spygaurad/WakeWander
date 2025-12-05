"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('messages', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create itineraries table
    op.create_table(
        'itineraries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('destination', sa.String(length=255), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('budget', sa.Integer(), nullable=False),
        sa.Column('season', sa.String(length=50), nullable=True),
        sa.Column('travel_dates', sa.String(length=100), nullable=True),
        sa.Column('plan', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('budget_allocation', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('itineraries')
    op.drop_table('conversations')