"""
routes/verification.py
Blueprint de vérification des bulletins via QR code
"""

from flask import Blueprint, render_template, request, abort, current_app
from models import db, BulletinVerification, Eleve, Classe, Ecole, Note, Matiere
from datetime import datetime
import os

verification_bp = Blueprint('verification', __name__)


def _get_base_url():
    """Retourne l'URL de base de l'application (Railway ou localhost)"""
    base = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    if base:
        return f'https://{base}'
    base = os.environ.get('APP_BASE_URL')
    if base:
        return base.rstrip('/')
    return 'http://127.0.0.1:5000'


def generer_qr_base64(url: str) -> str:
    """
    Génère un QR code en base64 pour l'URL donnée.
    Utilise qrcode + Pillow.
    pip install qrcode[pil]
    """
    try:
        import qrcode
        import io
        import base64
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=6,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0d1117', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{b64}'
    except Exception as e:
        print(f"⚠️ QR code non généré : {e}")
        return None


def get_verification_url(code: str) -> str:
    """Retourne l'URL publique de vérification d'un bulletin"""
    base = _get_base_url()
    return f'{base}/verifier/{code}'


def obtenir_ou_creer_verif(eleve_id, classe_id, annee_scolaire):
    """
    Raccourci utilisé dans les routes PDF pour obtenir
    le code + l'URL + le QR code d'un bulletin.
    Retourne un dict avec: code, url, qr_base64
    """
    from models import BulletinVerification
    verif = BulletinVerification.generer_ou_obtenir(eleve_id, classe_id, annee_scolaire)
    url   = get_verification_url(verif.code)
    qr    = generer_qr_base64(url)
    return {
        'code':       verif.code,
        'url':        url,
        'qr_base64':  qr,
    }


# ══════════════════════════════════════════════════════════════
#  ROUTE PUBLIQUE — Vérification du bulletin
# ══════════════════════════════════════════════════════════════

@verification_bp.route('/verifier/<string:code>')
def verifier_bulletin(code):
    """
    Page publique accessible sans connexion.
    Scanne le QR code → affiche le bulletin officiel.
    """

    # Chercher le code de vérification
    verif = BulletinVerification.query.filter_by(code=code).first()
    if not verif:
        return render_template('bulletin_verify.html',
                               valide=False,
                               erreur="Ce bulletin n'existe pas ou le code est invalide.")

    # Mettre à jour les stats de scan
    verif.nb_scans += 1
    verif.dernier_scan = datetime.utcnow()
    db.session.commit()

    # Charger les données
    eleve  = verif.eleve
    classe = verif.classe
    ecole  = Ecole.query.get(classe.ecole_id)
    matieres = Matiere.query.filter_by(classe_id=classe.id).all()

    # Notes par trimestre
    def get_notes_trim(trim):
        notes = []
        for mat in matieres:
            note = Note.query.filter_by(
                eleve_id=eleve.id,
                matiere_id=mat.id,
                trimestre=trim
            ).first()
            notes.append({
                'matiere': mat.nom,
                'note':    note.valeur if note else None,
            })
        return notes

    matieres_notes_t1 = get_notes_trim('T1')
    matieres_notes_t2 = get_notes_trim('T2')
    matieres_notes_t3 = get_notes_trim('T3')

    def moyenne_trim(notes_list):
        vals = [n['note'] for n in notes_list if n['note'] is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    moyennes = {
        'T1': moyenne_trim(matieres_notes_t1),
        'T2': moyenne_trim(matieres_notes_t2),
        'T3': moyenne_trim(matieres_notes_t3),
    }

    # Moyenne annuelle
    toutes_vals = [
        n['note']
        for lst in [matieres_notes_t1, matieres_notes_t2, matieres_notes_t3]
        for n in lst if n['note'] is not None
    ]
    moyenne = round(sum(toutes_vals) / len(toutes_vals), 2) if toutes_vals else 0.0

    # Classement
    eleves_classe = Eleve.query.filter_by(classe_id=classe.id).all()
    moyennes_classe = []
    for e in eleves_classe:
        notes_e = Note.query.filter_by(eleve_id=e.id).with_entities(Note.valeur).all()
        vals_e = [n.valeur for n in notes_e if n.valeur is not None]
        moy_e = round(sum(vals_e) / len(vals_e), 2) if vals_e else 0.0
        moyennes_classe.append((e.id, moy_e))

    moyennes_classe.sort(key=lambda x: x[1], reverse=True)
    rang = next((i + 1 for i, (eid, _) in enumerate(moyennes_classe) if eid == eleve.id), '—')
    total_eleves = len(eleves_classe)

    return render_template('bulletin_verify.html',
        valide=True,
        verif=verif,
        eleve=eleve,
        classe=classe,
        ecole=ecole,
        matieres_notes_t1=matieres_notes_t1,
        matieres_notes_t2=matieres_notes_t2,
        matieres_notes_t3=matieres_notes_t3,
        moyennes=moyennes,
        moyenne=moyenne,
        rang=rang,
        total_eleves=total_eleves,
    )