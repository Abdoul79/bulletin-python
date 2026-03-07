from flask import Blueprint, session, redirect, request, url_for
from i18n import LANGUAGES

language_bp = Blueprint('language', __name__, url_prefix='/lang')

@language_bp.route('/set/<language>')
def set_language(language=None):
    """Change la langue de l'interface"""
    if language in LANGUAGES.keys():
        session['language'] = language
    
    # Rediriger vers la page précédente ou le dashboard
    return redirect(request.referrer or url_for('main.dashboard'))