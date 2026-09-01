from flask import Blueprint, render_template, make_response, session, redirect, url_for, flash, request
from models import db, Classe, Matiere, Eleve, Note, Ecole
from utils import login_required, calculer_classement, get_eleve_rang
import zipfile
import io
from datetime import datetime
from urllib.parse import quote
from routes.verification import obtenir_ou_creer_verif

# Import WeasyPrint de façon sécurisée pour éviter les crashes
WEASYPRINT_AVAILABLE = False
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    print("✅ WeasyPrint disponible - Génération PDF activée")
except Exception as e:
    print(f"⚠️ WeasyPrint non disponible - Génération PDF désactivée: {e}")
    weasyprint = None

# Blueprint pour les bulletins français
pdf_bp = Blueprint('pdf', __name__, url_prefix='/bulletin')

# Blueprint pour les bulletins arabes
pdf_ar_bp = Blueprint('pdf_ar', __name__, url_prefix='/bulletin_ar')


# ============================================================================
# FONCTIONS UTILITAIRES COMMUNES
# ============================================================================

def _calculer_moyenne_classe(classe_id):
    """Calcule la moyenne générale de la classe"""
    eleves = Eleve.query.filter_by(classe_id=classe_id).all()
    moyennes_eleves = []
    
    for eleve in eleves:
        notes_eleve = Note.query.filter_by(eleve_id=eleve.id, statut='active').all()
        if notes_eleve:
            moyenne = sum([n.note for n in notes_eleve]) / len(notes_eleve)
            moyennes_eleves.append(moyenne)
    
    if moyennes_eleves:
        return round(sum(moyennes_eleves) / len(moyennes_eleves), 2)
    return 0.0


def _generer_appreciation(moyenne):
    """Génère une appréciation en français basée sur la moyenne"""
    if moyenne >= 16:
        return "Excellent travail, continuez ainsi !"
    elif moyenne >= 14:
        return "Très bon travail, félicitations !"
    elif moyenne >= 12:
        return "Bon travail, mais peut mieux faire."
    elif moyenne >= 10:
        return "Travail satisfaisant, des efforts sont nécessaires."
    elif moyenne >= 8:
        return "Travail insuffisant, il faut redoubler d'efforts."
    else:
        return "Résultats préoccupants, un suivi particulier est nécessaire."


def _generer_appreciation_ar(moyenne):
    """Génère une appréciation en arabe basée sur la moyenne"""
    if moyenne >= 16:
        return "نتائج ممتازة! استمر على هذا النهج."
    elif moyenne >= 14:
        return "نتائج جيدة جداً. أحسنت!"
    elif moyenne >= 12:
        return "نتائج جيدة، لكن يمكن التحسين."
    elif moyenne >= 10:
        return "نتائج مقبولة، مطلوب بذل مزيد من الجهد."
    elif moyenne >= 8:
        return "نتائج ضعيفة، يجب بذل جهد أكبر."
    else:
        return "نتائج مقلقة، يُوصى بمتابعة خاصة."


def _preparer_donnees_bulletin(eleve):
    """Prépare les données communes pour un bulletin"""
    classe = eleve.classe
    matieres = Matiere.query.filter_by(classe_id=classe.id).all()
    matiere_dict = {m.id: m.nom for m in matieres}

    trimestres = ['T1', 'T2', 'T3']
    notes_data = {t: {} for t in trimestres}

    for trimestre in trimestres:
        notes = Note.query.filter_by(
            eleve_id=eleve.id,
            trimestre=trimestre,
            statut='active'
        ).all()
        for note in notes:
            notes_data[trimestre][note.matiere_id] = note.note

    moyennes = {}
    for trimestre in trimestres:
        notes = list(notes_data[trimestre].values())
        moyennes[trimestre] = round(sum(notes) / len(notes), 2) if notes else 0.0

    moyennes_valides = [m for m in moyennes.values() if m > 0]
    moyenne_generale = round(sum(moyennes_valides) / len(moyennes_valides), 2) if moyennes_valides else 0.0

    def get_matiere_notes(trimestre_notes):
        result = []
        for matiere_id in matiere_dict.keys():
            note = trimestre_notes.get(matiere_id, None)
            result.append({
                'matiere': matiere_dict[matiere_id],
                'note': round(note, 2) if note is not None else None
            })
        return result

    matieres_notes_t1 = get_matiere_notes(notes_data['T1'])
    matieres_notes_t2 = get_matiere_notes(notes_data['T2'])
    matieres_notes_t3 = get_matiere_notes(notes_data['T3'])

    rang, total_eleves = get_eleve_rang(eleve.id, classe.id)
    moyenne_classe = _calculer_moyenne_classe(classe.id)

    return {
        'eleve': eleve,
        'classe': classe,
        'ecole': classe.ecole,
        'moyenne': moyenne_generale,
        'moyennes': moyennes,
        'matieres_notes_t1': matieres_notes_t1,
        'matieres_notes_t2': matieres_notes_t2,
        'matieres_notes_t3': matieres_notes_t3,
        'rang': rang,
        'total_eleves': total_eleves,
        'moyenne_classe': moyenne_classe,
        'annee_scolaire': classe.annee_scolaire
    }


def safe_filename_header(filename_ascii, filename_utf8=None):
    """
    Génère un header Content-Disposition sécurisé avec support UTF-8
    selon la RFC 2231 - RETOURNE UNE CHAÎNE 100% ASCII
    """
    # Nettoyer le nom ASCII
    filename_ascii = filename_ascii.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Supprimer les caractères non-ASCII
    clean_ascii = ""
    for char in filename_ascii:
        if ord(char) < 128 and char not in '<>:"|?*':
            clean_ascii += char
        else:
            clean_ascii += "_"
    
    if not clean_ascii.strip("._"):
        clean_ascii = "document.pdf"
    
    if filename_utf8:
        # Nettoyer le nom UTF-8
        filename_utf8 = filename_utf8.replace(' ', '_').replace('/', '_').replace('\\', '_')
        # quote() retourne une chaîne ASCII, donc pas de problème d'encodage
        encoded = quote(filename_utf8)
        return 'filename="' + clean_ascii + '"; filename*=UTF-8\'\'' + encoded
    else:
        return 'filename="' + clean_ascii + '"'


# ============================================================================
# ROUTES FRANÇAIS (Blueprint 'pdf')
# ============================================================================

@pdf_bp.route('/pdf/<int:eleve_id>')
@login_required
def generer_bulletin_pdf(eleve_id):
    """Génération du bulletin PDF pour un élève (français)"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible. WeasyPrint n'est pas correctement installe.", "error")
        flash("Vous pouvez utiliser la previsualisation HTML a la place.", "info")
        return redirect(url_for('pdf.preview_bulletin', eleve_id=eleve_id))
    
    eleve = Eleve.query.get_or_404(eleve_id)
    classe = eleve.classe
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    try:
        donnees = _preparer_donnees_bulletin(eleve)
        donnees['appreciation'] = _generer_appreciation(donnees['moyenne'])

        qr_info = obtenir_ou_creer_verif(eleve.id, classe.id, classe.annee_scolaire)
        html = render_template('bulletin_pdf.html', **donnees, qr_info=qr_info)
        pdf = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        
        filename = f"bulletin_{eleve.prenom}_{eleve.nom}_{classe.nom}_{classe.annee_scolaire}.pdf"
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(filename)
        
        return response

    except Exception as e:
        flash(f"Erreur lors de la generation du PDF : {str(e)}", "error")
        flash("Essayez la previsualisation HTML a la place.", "info")
        return redirect(url_for('pdf.preview_bulletin', eleve_id=eleve_id))


@pdf_bp.route('/preview/<int:eleve_id>')
@login_required
def preview_bulletin(eleve_id):
    """Prévisualisation HTML du bulletin (français)"""
    
    eleve = Eleve.query.get_or_404(eleve_id)
    classe = eleve.classe
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    donnees = _preparer_donnees_bulletin(eleve)
    donnees['appreciation'] = _generer_appreciation(donnees['moyenne'])
    donnees['weasyprint_available'] = WEASYPRINT_AVAILABLE
     
    qr_info = obtenir_ou_creer_verif(eleve.id, classe.id, classe.annee_scolaire)
    return render_template('bulletin_preview.html', **donnees, qr_info=qr_info)


@pdf_bp.route('/classe/<int:classe_id>')
@login_required
def generer_bulletins_classe(classe_id):
    """Génère un ZIP avec tous les bulletins de la classe (ordre alphabétique - français)"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible. WeasyPrint n'est pas correctement installe.", "error")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))
    
    classe = Classe.query.get_or_404(classe_id)
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))
    
    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).order_by(Eleve.nom, Eleve.prenom).all()
    
    if not eleves:
        flash("Aucun eleve dans cette classe.", "warning")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))
    
    try:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for eleve in eleves:
                try:
                    donnees = _preparer_donnees_bulletin(eleve)
                    donnees['appreciation'] = _generer_appreciation(donnees['moyenne'])
                    
                    
                    html = render_template('bulletin_pdf.html', **donnees)
                    pdf_data = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
                    
                    filename = f"bulletin_{eleve.prenom}_{eleve.nom}.pdf"
                    filename = filename.replace(' ', '_').replace('/', '_')
                    
                    zip_file.writestr(filename, pdf_data)
                    
                except Exception as e:
                    print(f"Erreur pour l'eleve {eleve.prenom} {eleve.nom}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        zip_filename = f"bulletins_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d')}.zip"
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(zip_filename)
        
        flash(f"Bulletins generes avec succes pour {len(eleves)} eleve(s).", "success")
        return response
        
    except Exception as e:
        flash(f"Erreur lors de la generation des bulletins : {str(e)}", "error")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))


@pdf_bp.route('/classe_classee/<int:classe_id>')
@login_required
def generer_bulletins_classe_classee(classe_id):
    """Génère un ZIP avec tous les bulletins triés par classement (français)"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible. WeasyPrint n'est pas correctement installe.", "error")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))
    
    classe = Classe.query.get_or_404(classe_id)
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))
    
    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    
    if not eleves:
        flash("Aucun eleve dans cette classe.", "warning")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))
    
    try:
        classement_data = calculer_classement(classe_id)
        
        if not classement_data:
            flash("Impossible de calculer le classement : aucune note disponible.", "warning")
            return redirect(url_for('main.voir_classe', classe_id=classe_id))
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for rang, (eleve_id, moyenne_generale, eleve) in enumerate(classement_data, 1):
                try:
                    donnees = _preparer_donnees_bulletin(eleve)
                    donnees['rang'] = rang
                    donnees['total_eleves'] = len(classement_data)
                    donnees['moyenne'] = moyenne_generale
                    donnees['appreciation'] = _generer_appreciation(moyenne_generale)
                    

                    html = render_template('bulletin_pdf.html', **donnees)
                    pdf_data = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
                    
                    filename = f"{rang:02d}_{eleve.prenom}_{eleve.nom}_({moyenne_generale:.2f}).pdf"
                    filename = filename.replace(' ', '_').replace('/', '_')
                    
                    zip_file.writestr(filename, pdf_data)
                    
                except Exception as e:
                    print(f"Erreur pour l'eleve {eleve.prenom} {eleve.nom}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        zip_filename = f"bulletins_classes_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(zip_filename)
        
        flash(f"Bulletins generes avec succes pour {len(classement_data)} eleve(s) classes par rang.", "success")
        return response
        
    except Exception as e:
        flash(f"Erreur lors de la generation des bulletins : {str(e)}", "error")
        return redirect(url_for('main.voir_classe', classe_id=classe_id))


# ============================================================================
# ROUTES ARABE (Blueprint 'pdf_ar')
# ============================================================================

@pdf_ar_bp.route('/preview/<int:eleve_id>')
@login_required
def preview_bulletin_ar(eleve_id):
    """Prévisualisation HTML du bulletin en arabe"""
    
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    eleve = Eleve.query.get_or_404(eleve_id)
    classe = eleve.classe
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard_ar'))

    donnees = _preparer_donnees_bulletin(eleve)
    donnees['appreciation'] = _generer_appreciation_ar(donnees['moyenne'])
    donnees['weasyprint_available'] = WEASYPRINT_AVAILABLE

    qr_info = obtenir_ou_creer_verif(eleve.id, classe.id, classe.annee_scolaire)
    return render_template('bulletin_preview_ar.html', **donnees, qr_info=qr_info)


@pdf_ar_bp.route('/pdf/<int:eleve_id>')
@login_required
def generer_bulletin_pdf_ar(eleve_id):
    """Génération du bulletin PDF en arabe"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible. WeasyPrint n'est pas correctement installe.", "error")
        return redirect(url_for('pdf_ar.preview_bulletin_ar', eleve_id=eleve_id))

    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    eleve = Eleve.query.get_or_404(eleve_id)
    classe = eleve.classe
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard_ar'))

    try:
        donnees = _preparer_donnees_bulletin(eleve)
        donnees['appreciation'] = _generer_appreciation_ar(donnees['moyenne'])

        qr_info = obtenir_ou_creer_verif(eleve.id, classe.id, classe.annee_scolaire)
        html = render_template('bulletin_pdf_ar.html', **donnees, qr_info=qr_info)
        pdf = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        
        # Nom ASCII pour compatibilité
        filename_ascii = f"bulletin_ar_{eleve.prenom}_{eleve.nom}_{classe.nom}_{classe.annee_scolaire}.pdf"
        # Nom en arabe pour les navigateurs modernes
        filename_utf8 = f"نشرة_{eleve.prenom}_{eleve.nom}_{classe.nom}_{classe.annee_scolaire}.pdf"
        
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(filename_ascii, filename_utf8)
        return response
        
    except Exception as e:
        flash(f"Erreur lors de la generation du PDF: {str(e)}", "error")
        return redirect(url_for('pdf_ar.preview_bulletin_ar', eleve_id=eleve_id))


@pdf_ar_bp.route('/classe/<int:classe_id>')
@login_required
def generer_bulletins_classe_ar(classe_id):
    """Génère un ZIP avec bulletins par ordre alphabétique (arabe)"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible.", "error")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard_ar'))

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).order_by(Eleve.nom, Eleve.prenom).all()
    
    if not eleves:
        flash("Aucun eleve dans cette classe.", "warning")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

    try:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for eleve in eleves:
                try:
                    donnees = _preparer_donnees_bulletin(eleve)
                    donnees['appreciation'] = _generer_appreciation_ar(donnees['moyenne'])
                    
                    html = render_template('bulletin_pdf_ar.html', **donnees)
                    pdf_data = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
                    
                    # Utiliser un nom ASCII pour les fichiers dans le ZIP (évite les problèmes d'encodage)
                    filename = f"bulletin_ar_{eleve.prenom}_{eleve.nom}.pdf"
                    filename = filename.replace(' ', '_').replace('/', '_')
                    
                    zip_file.writestr(filename, pdf_data)
                    
                except Exception as e:
                    print(f"Erreur pour l'eleve {eleve.prenom} {eleve.nom}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        # Nom ASCII pour compatibilité
        zip_filename_ascii = f"bulletins_ar_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d')}.zip"
        # Nom en arabe pour les navigateurs modernes
        zip_filename_utf8 = f"نشرات_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d')}.zip"
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(zip_filename_ascii, zip_filename_utf8)
        
        flash(f"Bulletins generes avec succes pour {len(eleves)} eleve(s).", "success")
        return response
        
    except Exception as e:
        flash(f"Erreur lors de la generation des bulletins: {str(e)}", "error")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))


@pdf_ar_bp.route('/classe_classee/<int:classe_id>')
@login_required
def generer_bulletins_classe_classee_ar(classe_id):
    """Génère un ZIP avec bulletins triés par classement (arabe)"""
    
    if not WEASYPRINT_AVAILABLE:
        flash("Generation PDF non disponible.", "error")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    
    if classe.ecole_id != session['ecole_id']:
        flash("Acces non autorise.", "error")
        return redirect(url_for('main.dashboard_ar'))

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    
    if not eleves:
        flash("Aucun eleve dans cette classe.", "warning")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

    try:
        classement_data = calculer_classement(classe_id)
        
        if not classement_data:
            flash("Impossible de calculer le classement: aucune note disponible.", "warning")
            return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for rang, (eleve_id, moyenne_generale, eleve) in enumerate(classement_data, 1):
                try:
                    donnees = _preparer_donnees_bulletin(eleve)
                    donnees['rang'] = rang
                    donnees['total_eleves'] = len(classement_data)
                    donnees['moyenne'] = moyenne_generale
                    donnees['appreciation'] = _generer_appreciation_ar(moyenne_generale)

                    html = render_template('bulletin_pdf_ar.html', **donnees)
                    pdf_data = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
                    
                    # Utiliser un nom ASCII pour les fichiers dans le ZIP#
                    filename = f"{rang:02d}_bulletin_ar_{eleve.prenom}_{eleve.nom}_({moyenne_generale:.2f}).pdf"
                    filename = filename.replace(' ', '_').replace('/', '_')
                    
                    zip_file.writestr(filename, pdf_data)
                    
                except Exception as e:
                    print(f"Erreur pour l'eleve {eleve.prenom} {eleve.nom}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        # Nom ASCII pour compatibilité
        zip_filename_ascii = f"bulletins_ar_classes_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d')}.zip"
        # Nom en arabe pour les navigateurs modernes
        zip_filename_utf8 = f"نشرات_مرتبة_{classe.nom}_{classe.annee_scolaire}_{datetime.now().strftime('%Y%m%d')}.zip"
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; ' + safe_filename_header(zip_filename_ascii, zip_filename_utf8)
        
        flash(f"Bulletins generes avec succes pour {len(classement_data)} eleve(s) classes par rang.", "success")
        return response
        
    except Exception as e:
        flash(f"Erreur lors de la generation des bulletins: {str(e)}", "error")
        return redirect(url_for('main.voir_classe_ar', classe_id=classe_id))

