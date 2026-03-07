"""
Script de migration pour ajouter la colonne matricule
Exécutez ce script avec : python migrate_matricule.py
"""

import sqlite3
import sys
from datetime import date

def generer_matricule(eleve_id, classe_id, ecole_id, count):
    """Génère un matricule unique"""
    annee = date.today().year
    return f"E{ecole_id:03d}-C{classe_id:03d}-{annee}-{count:04d}"

def migrate():
    # Nom de votre fichier de base de données
    DB_FILE = 'instance/school.db'  # Modifiez selon votre configuration
    
    try:
        print("=== MIGRATION BASE DE DONNÉES ===")
        print(f"Fichier: {DB_FILE}\n")
        
        # Connexion à la base de données
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Vérifier si la colonne existe déjà
        cursor.execute("PRAGMA table_info(eleve)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'matricule' in columns:
            print("⚠️  La colonne 'matricule' existe déjà!")
            print("Voulez-vous régénérer les matricules pour tous les élèves? (o/n): ", end='')
            reponse = input().strip().lower()
            if reponse != 'o':
                print("Migration annulée")
                conn.close()
                return
        else:
            # Ajouter la colonne matricule
            print("1. Ajout de la colonne 'matricule'...")
            cursor.execute("ALTER TABLE eleve ADD COLUMN matricule VARCHAR(50)")
            print("   ✓ Colonne ajoutée\n")
        
        # Générer les matricules pour tous les élèves
        print("2. Génération des matricules...")
        
        # Récupérer tous les élèves avec leurs informations de classe
        cursor.execute("""
            SELECT e.id, e.prenom, e.nom, e.classe_id, c.ecole_id
            FROM eleve e
            JOIN classe c ON e.classe_id = c.id
            ORDER BY c.ecole_id, e.classe_id, e.id
        """)
        
        eleves = cursor.fetchall()
        
        if not eleves:
            print("   ⚠️  Aucun élève trouvé dans la base de données")
            conn.close()
            return
        
        # Compter les élèves par classe pour le numéro séquentiel
        classe_counts = {}
        matricules_generes = []
        
        for eleve_id, prenom, nom, classe_id, ecole_id in eleves:
            # Incrémenter le compteur pour cette classe
            if classe_id not in classe_counts:
                classe_counts[classe_id] = 1
            else:
                classe_counts[classe_id] += 1
            
            # Générer le matricule
            matricule = generer_matricule(
                eleve_id, 
                classe_id, 
                ecole_id, 
                classe_counts[classe_id]
            )
            
            # Vérifier l'unicité
            while matricule in matricules_generes:
                classe_counts[classe_id] += 1
                matricule = generer_matricule(
                    eleve_id, 
                    classe_id, 
                    ecole_id, 
                    classe_counts[classe_id]
                )
            
            matricules_generes.append(matricule)
            
            # Mettre à jour la base de données
            cursor.execute(
                "UPDATE eleve SET matricule = ? WHERE id = ?",
                (matricule, eleve_id)
            )
            
            print(f"   {len(matricules_generes)}. {prenom} {nom} → {matricule}")
        
        # Valider les changements
        conn.commit()
        
        print(f"\n✓ Migration terminée avec succès!")
        print(f"✓ {len(matricules_generes)} matricule(s) généré(s)")
        
        # Créer un index pour améliorer les performances
        print("\n3. Création d'un index sur la colonne matricule...")
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_eleve_matricule ON eleve(matricule)")
            conn.commit()
            print("   ✓ Index créé")
        except Exception as e:
            print(f"   ⚠️  Index non créé: {e}")
        
        conn.close()
        
        print("\n" + "="*50)
        print("✓ MIGRATION COMPLÈTE!")
        print("="*50)
        
    except sqlite3.Error as e:
        print(f"\n✗ Erreur SQLite: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n✗ Erreur: Fichier de base de données '{DB_FILE}' introuvable")
        print("   Veuillez modifier la variable DB_FILE dans le script")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("\n⚠️  ATTENTION: Ce script va modifier votre base de données")
    print("   Assurez-vous d'avoir une sauvegarde!\n")
    print("Voulez-vous continuer? (o/n): ", end='')
    
    reponse = input().strip().lower()
    if reponse == 'o':
        migrate()
    else:
        print("\nMigration annulée")

