from flask import session, request
from flask_babel import Babel, get_locale

babel = Babel()

# Langues supportées
LANGUAGES = {
    'fr': 'Français',
    'ar': 'العربية'
}

def init_babel(app):
    """Initialiser Babel avec l'application Flask"""
    babel.init_app(app)
    
    # Configuration Babel
    app.config['LANGUAGES'] = LANGUAGES
    app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

@babel.localeselector
def get_locale():
    """Détermine la langue à utiliser"""
    # 1. Langue en session (choix utilisateur)
    if 'language' in session:
        return session['language']
    
    # 2. Langue du navigateur
    return request.accept_languages.best_match(LANGUAGES.keys()) or 'fr'

def get_current_language():
    """Retourne la langue actuelle"""
    return get_locale()

def get_available_languages():
    """Retourne toutes les langues disponibles"""
    return LANGUAGES
