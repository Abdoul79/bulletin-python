import os
from dotenv import load_dotenv

load_dotenv()  # charge le fichier .env

class Config:
    # ── Clé secrète Flask ──────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_fallback_change_moi')

    # ── Base de données ────────────────────────────────
    _db_url = os.environ.get('DATABASE_URL', '')

    # Supabase/Heroku utilisent parfois "postgres://" → on corrige en "postgresql://"
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url if _db_url else 'sqlite:///bulletin.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Upload fichiers ────────────────────────────────
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max

