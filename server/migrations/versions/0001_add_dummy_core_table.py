from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_dummy_core_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'dummy_core_table',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('dummy_core_table')

