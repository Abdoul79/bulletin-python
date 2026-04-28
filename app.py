from flask import Flask, session, redirect, url_for, request, flash
from dotenv import load_dotenv
from config import Config
from models import db, migrate
from i18n import init_babel, get_current_language, get_available_languages
from routes.analytics import analytics_bp
from translations_manual import t
from datetime import datetime, timedelta
from routes.absences import absences_bp


import os

load_dotenv()  # ← charge .env au démarrage

# ======================================
# CONFIGURATION TIMEOUT DE SESSION
# ======================================
SESSION_TIMEOUT_MINUTES = 60  # 1 heure

PUBLIC_ENDPOINTS = {
    'auth.login',
    'auth.admin_login',
    'auth.index',
    'auth.logout',
    'auth.admin_logout',
    'language.change_language',
    'static',
}


# ══════════════════════════════════════════════════════════════
#  TEST DE CONNEXION — Supabase ou SQLite
# ══════════════════════════════════════════════════════════════

def test_db_connection(uri: str) -> bool:
    """
    Tente une connexion rapide à l'URI donnée.
    Retourne True si la connexion réussit, False sinon.
    """
    try:
        if 'postgresql' in uri or 'postgres' in uri:
            import psycopg2
            from urllib.parse import urlparse
            parsed = urlparse(uri)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                dbname=parsed.path.lstrip('/'),
                connect_timeout=5,          # ← timeout 5 secondes max
                sslmode='require',
            )
            conn.close()
            return True
        else:
            # SQLite → toujours disponible
            return True
    except Exception as e:
        print(f"⚠️  Connexion DB échouée : {e}")
        return False


def get_db_uri() -> str:
    """
    Retourne l'URI à utiliser :
    1. Essaie DATABASE_URL (Supabase)
    2. Si indisponible → bascule sur SQLite local
    """
    supabase_uri = os.environ.get('DATABASE_URL', '')

    # Normaliser postgres:// → postgresql:// (SQLAlchemy exige postgresql://)
    if supabase_uri.startswith('postgres://'):
        supabase_uri = supabase_uri.replace('postgres://', 'postgresql://', 1)

    if supabase_uri and ('postgresql' in supabase_uri or 'postgres' in supabase_uri):
        print("🔌 Test de connexion à Supabase...")
        if test_db_connection(supabase_uri):
            print("✅ Supabase disponible → connexion établie")
            return supabase_uri
        else:
            print("❌ Supabase INDISPONIBLE → bascule sur SQLite local")
            return 'sqlite:///bulletin_fallback.db'

    # Pas de DATABASE_URL → SQLite direct
    sqlite_uri = os.environ.get('SQLITE_URL', 'sqlite:///bulletin.db')
    print(f"⚠️  Pas de DATABASE_URL → SQLite : {sqlite_uri}")
    return sqlite_uri


def create_app():
    app = Flask(__name__)

    # ── Configuration de base ──────────────────────────
    app.config.from_object(Config)

    # ── Déterminer la base de données à utiliser ───────
    db_uri = get_db_uri()
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    # ── Log de confirmation ────────────────────────────
    if 'postgresql' in db_uri:
        print("✅ Base de données : Supabase (PostgreSQL)")
    else:
        print(f"⚠️  Base de données : SQLite local → {db_uri}")

    # ── Extensions ─────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)

    # ── Babel / Traductions ────────────────────────────
    init_babel(app)

    # ── Blueprints ─────────────────────────────────────
    register_routes(app)

    # ── Indicateur base active dans templates ──────────
    @app.context_processor
    def inject_conf_vars():
        is_fallback = 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', '')
        return {
            't': t,
            'current_lang': get_current_language(),
            'available_languages': get_available_languages(),
            'db_fallback': is_fallback,   # ← dispo dans tous les templates
        }

    # ── Timeout de session global ──────────────────────
    @app.before_request
    def check_session_timeout():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
            return

        if 'last_activity' in session:
            last = datetime.fromisoformat(session['last_activity'])
            if datetime.utcnow() - last > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                user_type = session.get('user_type', 'ecole')
                session.clear()
                flash("⏰ Votre session a expiré. Veuillez vous reconnecter.", "warning")
                if user_type == 'admin':
                    return redirect(url_for('auth.admin_login'))
                return redirect(url_for('auth.login'))

        if session.get('user_type') in ('admin', 'ecole'):
            session['last_activity'] = datetime.utcnow().isoformat()
            session.modified = True

    # ── Créer les tables si elles n'existent pas ───────
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tables vérifiées / créées")
        except Exception as e:
            print(f"❌ Erreur création tables : {e}")

    return app


def register_routes(app):
    try:
        from routes.auth      import auth_bp
        from routes.main      import main_bp
        from routes.classe    import classe_bp
        from routes.eleve     import eleve_bp
        from routes.matiere   import matiere_bp
        from routes.notes     import notes_bp
        from routes.pdf       import pdf_bp, pdf_ar_bp
        from routes.language  import language_bp
        from routes.search    import search_bp
        from routes.paiements import paiements_bp
        from routes.absences  import absences_bp

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
        app.register_blueprint(analytics_bp)
        app.register_blueprint(absences_bp)
        print("✅ Tous les blueprints enregistrés")

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Vérifiez que tous les fichiers routes existent")


# ── IMPORTANT : variable app accessible par gunicorn ──
app = create_app()

if __name__ == '__main__':
    print("🚀 Application démarrée sur http://127.0.0.1:5000")
    app.run(debug=True)