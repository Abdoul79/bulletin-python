from flask import Flask
from dotenv import load_dotenv
from config import Config
from models import db, migrate
from i18n import init_babel, get_current_language, get_available_languages
from translations_manual import t
import os

load_dotenv()  # ← charge .env au démarrage


def create_app():
    app = Flask(__name__)


    # ── Configuration ──────────────────────────────────
    app.config.from_object(Config)

    # ── Log pour confirmer la base utilisée ───────────
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'postgresql' in db_uri or 'supabase' in db_uri:
        print("✅ Base de données : Supabase (PostgreSQL)")
    else:
        print("⚠️  Base de données : SQLite local (développement)")

    # ── Extensions ─────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)

    # ── Babel / Traductions ────────────────────────────
    init_babel(app)

    # ── Blueprints ─────────────────────────────────────
    register_routes(app)

    # ── Contexte global templates ──────────────────────
    @app.context_processor
    def inject_conf_vars():
        return {
            't': t,
            'current_lang': get_current_language(),
            'available_languages': get_available_languages()
        }

    # ── Créer les tables si elles n'existent pas ───────
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tables vérifiées / créées")
        except Exception as e:
            print(f"❌ Erreur création tables : {e}")

    return app

# ... tout le reste du code ...

def register_routes(app):
    try:
        from routes.auth     import auth_bp
        from routes.main     import main_bp
        from routes.classe   import classe_bp
        from routes.eleve    import eleve_bp
        from routes.matiere  import matiere_bp
        from routes.notes    import notes_bp
        from routes.pdf      import pdf_bp, pdf_ar_bp
        from routes.language import language_bp
        from routes.search   import search_bp
        from routes.paiements import paiements_bp

        app.register_blueprint(search_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(classe_bp)
        app.register_blueprint(eleve_bp)
        app.register_blueprint(matiere_bp)
        app.register_blueprint(notes_bp)
        app.register_blueprint(pdf_bp)
        app.register_blueprint(pdf_ar_bp)
        app.register_blueprint(language_bp)
        app.register_blueprint(paiements_bp)
        print("✅ Tous les blueprints enregistrés")

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Vérifiez que tous les fichiers routes existent")


# ── IMPORTANT : variable app accessible par gunicorn ──
app = create_app()

if __name__ == '__main__':
    print("🚀 Application démarrée sur http://127.0.0.1:5000")
    app.run(debug=True)
