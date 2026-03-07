from .auth import auth_bp
from .main import main_bp
from .classe import classe_bp
from .eleve import eleve_bp
from .matiere import matiere_bp
from .notes import notes_bp
from .pdf import pdf_bp


def register_routes(app):
    """Enregistrer tous les blueprints dans l'application Flask"""
    
    # Routes d'authentification
    app.register_blueprint(auth_bp)
    
    # Routes principales
    app.register_blueprint(main_bp)
    
    # Routes de gestion
    app.register_blueprint(classe_bp)
    app.register_blueprint(eleve_bp)
    app.register_blueprint(matiere_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(pdf_bp)