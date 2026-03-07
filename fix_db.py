"""
Script à exécuter UNE SEULE FOIS pour corriger la base de données.
Lance avec : python fix_db.py
"""
from app import app
from models import db

with app.app_context():
    with db.engine.connect() as conn:

        # Vérifier les colonnes existantes
        result = conn.execute(db.text("PRAGMA table_info('matricule_used')"))
        colonnes = [row[1] for row in result.fetchall()]
        print(f"Colonnes actuelles : {colonnes}")

        # Ajouter ecole_id si manquant
        if 'ecole_id' not in colonnes:
            conn.execute(db.text(
                "ALTER TABLE matricule_used ADD COLUMN ecole_id INTEGER DEFAULT 1"
            ))
            print("✅ Colonne ecole_id ajoutée")

        # Ajouter used_at si manquant
        if 'used_at' not in colonnes:
            conn.execute(db.text(
                "ALTER TABLE matricule_used ADD COLUMN used_at DATETIME"
            ))
            print("✅ Colonne used_at ajoutée")

        conn.commit()

        # Remplir ecole_id depuis les élèves existants
        conn.execute(db.text("""
            UPDATE matricule_used
            SET ecole_id = (
                SELECT c.ecole_id
                FROM eleve el
                JOIN classe c ON el.classe_id = c.id
                WHERE el.matricule = matricule_used.matricule
                LIMIT 1
            )
            WHERE ecole_id IS NULL OR ecole_id = 1
        """))

        # Fallback : mettre 1 si toujours NULL
        conn.execute(db.text(
            "UPDATE matricule_used SET ecole_id = 1 WHERE ecole_id IS NULL"
        ))

        conn.commit()

        # Vérifier le résultat final
        result = conn.execute(db.text("SELECT * FROM matricule_used"))
        rows = result.fetchall()
        print(f"\n📋 Contenu de matricule_used ({len(rows)} lignes) :")
        for row in rows:
            print(f"   {row}")

        # Vérifier les colonnes finales
        result = conn.execute(db.text("PRAGMA table_info('matricule_used')"))
        print(f"\n✅ Colonnes finales : {[row[1] for row in result.fetchall()]}")

    print("\n✅ Base de données corrigée avec succès !")