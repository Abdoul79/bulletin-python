"""add matiere and fix matricule

Revision ID: f53a31e36b21
Revises: eed65ff679ad
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f53a31e36b21'
down_revision = 'eed65ff679ad'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Supprimer l'ancienne contrainte unique globale sur eleve.matricule ──
    with op.batch_alter_table('eleve', schema=None) as batch_op:
        batch_op.drop_constraint('uq_eleve_matricule', type_='unique')

    # ── 2. Modifier les colonnes de matiere ──────────────────────────────────
    with op.batch_alter_table('matiere', schema=None) as batch_op:
        batch_op.alter_column('nom',
            existing_type=sa.VARCHAR(length=50),
            type_=sa.String(length=100),
            existing_nullable=False
        )
        batch_op.alter_column('jour',
            existing_type=sa.VARCHAR(length=10),
            type_=sa.String(length=20),
            existing_nullable=True
        )

    # ── 3. Ajouter ecole_id + contrainte unique nommée sur matricule_used ────
    with op.batch_alter_table('matricule_used', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('ecole_id', sa.Integer(), nullable=True)
        )

    # Remplir ecole_id pour les lignes existantes (via la table eleve → classe → ecole)
    op.execute("""
        UPDATE matricule_used
        SET ecole_id = (
            SELECT e.ecole_id
            FROM eleve el
            JOIN classe e ON el.classe_id = e.id
            WHERE el.matricule = matricule_used.matricule
            LIMIT 1
        )
        WHERE ecole_id IS NULL
    """)

    # Si des lignes ont encore ecole_id NULL (orphelines), mettre ecole_id = 1 par défaut
    op.execute("UPDATE matricule_used SET ecole_id = 1 WHERE ecole_id IS NULL")

    with op.batch_alter_table('matricule_used', schema=None) as batch_op:
        batch_op.alter_column('ecole_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_matricule_used_ecole',   # ← nom explicite obligatoire
            'ecole', ['ecole_id'], ['id']
        )
        batch_op.create_unique_constraint(
            'uq_matricule_ecole',        # ← nom explicite obligatoire
            ['matricule', 'ecole_id']
        )


def downgrade():
    with op.batch_alter_table('matricule_used', schema=None) as batch_op:
        batch_op.drop_constraint('uq_matricule_ecole', type_='unique')
        batch_op.drop_constraint('fk_matricule_used_ecole', type_='foreignkey')
        batch_op.drop_column('ecole_id')

    with op.batch_alter_table('matiere', schema=None) as batch_op:
        batch_op.alter_column('nom',
            existing_type=sa.String(length=100),
            type_=sa.VARCHAR(length=50),
            existing_nullable=False
        )
        batch_op.alter_column('jour',
            existing_type=sa.String(length=20),
            type_=sa.VARCHAR(length=10),
            existing_nullable=True
        )

    with op.batch_alter_table('eleve', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_eleve_matricule', ['matricule'])
