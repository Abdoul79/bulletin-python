from models import Note, Matiere, Eleve
from functools import wraps
from flask import session, redirect, url_for
from urllib.parse import quote

def login_required(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'ecole_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def calculer_moyennes(eleve_id, trimestre='T1'):
    """Calcule la moyenne générale d'un élève pour un trimestre donné"""
    notes = Note.query.filter_by(
        eleve_id=eleve_id, 
        trimestre=trimestre, 
        statut='active'
    ).all()
    
    if not notes:
        return 0.0, []

    matieres_notes = []
    total = 0.0
    
    for note in notes:
        matiere = Matiere.query.get(note.matiere_id)
        matieres_notes.append({
            'matiere': matiere.nom if matiere else 'Matière supprimée',
            'note': note.note
        })
        total += note.note

    moyenne_generale = total / len(notes)
    return round(moyenne_generale, 2), matieres_notes


def calculer_classement(classe_id):
    """Calcule le classement des élèves d'une classe"""
    eleves_classe = Eleve.query.filter_by(classe_id=classe_id).all()
    classement_data = []
    trimestres = ['T1', 'T2', 'T3']

    for eleve in eleves_classe:
        notes_annuelles = []
        for trimestre in trimestres:
            notes = Note.query.filter_by(
                eleve_id=eleve.id, 
                trimestre=trimestre, 
                statut='active'
            ).all()
            if notes:
                moyenne = sum([note.note for note in notes]) / len(notes)
                notes_annuelles.append(moyenne)
        
        if notes_annuelles:
            moyenne_generale = sum(notes_annuelles) / len(notes_annuelles)
            classement_data.append((eleve.id, moyenne_generale, eleve))

    # Trier par moyenne décroissante
    classement_data.sort(key=lambda x: x[1], reverse=True)
    return classement_data


def get_eleve_rang(eleve_id, classe_id):
    """Obtient le rang d'un élève dans sa classe"""
    classement = calculer_classement(classe_id)
    for rang, (eid, moyenne, eleve) in enumerate(classement, 1):
        if eid == eleve_id:
            return rang, len(classement)
    return "N/A", len(classement)


def format_filename(filename, prefix=""):
    """Formate un nom de fichier en supprimant les caractères spéciaux"""
    if not filename:
        return None
    
    # Remplacer les caractères problématiques
    safe_filename = filename.replace(' ', '_')
    safe_filename = safe_filename.replace('@', '_').replace('.', '_')
    
    if prefix:
        safe_filename = f"{prefix}_{safe_filename}"
    
    return safe_filename


def validate_note(note_value):
    """Valide une note (doit être entre 0 et 20)"""
    try:
        note = float(note_value)
        return 0 <= note <= 20, note
    except (ValueError, TypeError):
        return False, None


def get_trimestre_choices():
    """Retourne les choix de trimestres"""
    return [
        ('', 'Tous les trimestres'),
        ('T1', 'Premier Trimestre'),
        ('T2', 'Deuxième Trimestre'),
        ('T3', 'Troisième Trimestre')
    ]


def safe_filename(filename: str, filename_utf8: str = None) -> str:
    """
    Génère une chaîne Content-Disposition sécurisée compatible avec HTTP.
    Respecte la norme RFC 2231 pour les caractères non-ASCII.
    
    Args:
        filename: Nom de fichier ASCII (obligatoire)
        filename_utf8: Nom de fichier UTF-8 optionnel (pour navigateurs modernes)
    
    Usage:
        # Avec un seul nom (ASCII uniquement)
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename("bulletin.pdf")
        
        # Avec deux noms (ASCII + UTF-8)
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename(
            "bulletin_ar.pdf", 
            "نشرة_أحمد.pdf"
        )
    
    Returns:
        str: Chaîne formatée pour Content-Disposition (compatible latin-1)
    """
    # Nettoyer le nom ASCII
    ascii_name = filename.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Supprimer les caractères non-ASCII du nom de base
    ascii_clean = ""
    for c in ascii_name:
        if ord(c) < 128 and c not in '<>:"|?*':
            ascii_clean += c
        else:
            ascii_clean += "_"
    
    # Si le nom nettoyé est vide, utiliser un nom par défaut
    if not ascii_clean.strip("._"):
        ascii_clean = "document.pdf" if filename.endswith('.pdf') else "document.zip"
    
    # Si un nom UTF-8 est fourni, l'ajouter selon RFC 2231
    if filename_utf8:
        utf8_clean = filename_utf8.replace(' ', '_').replace('/', '_').replace('\\', '_')
        # IMPORTANT: quote() retourne une chaîne ASCII, donc pas de problème d'encodage
        encoded = quote(utf8_clean)
        return f'filename="{ascii_clean}"; filename*=UTF-8\'\'{encoded}'
    else:
        return f'filename="{ascii_clean}"'