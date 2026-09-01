from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Classe, Matiere, Note, Ecole
from utils import login_required
from datetime import datetime
from models import Professeur
matiere_bp = Blueprint('matiere', __name__, url_prefix='/ecole')


def check_horaire_conflict(classe_id, jour, heure_obj, duree, exclude_id=None):
    """
    Vérifie s'il y a un conflit d'horaire dans la classe.
    Retourne True s'il y a un conflit, False sinon.
    """
    if not jour or not heure_obj:
        return False

    query = Matiere.query.filter_by(classe_id=classe_id, jour=jour)
    if exclude_id:
        query = query.filter(Matiere.id != exclude_id)

    matieres_du_jour = query.all()

    from datetime import timedelta, date

    # Convertir en datetime pour comparer les plages
    base_date = date.today()
    new_start = datetime.combine(base_date, heure_obj)
    new_end = new_start + timedelta(hours=duree)

    for m in matieres_du_jour:
        if m.heure is None:
            continue
        existing_start = datetime.combine(base_date, m.heure)
        existing_end = existing_start + timedelta(hours=m.duree or 1)

        # Chevauchement si les plages se croisent
        if new_start < existing_end and new_end > existing_start:
            return True, m

    return False, None


def parse_heure(heure_str, redirect_url):
    """Parse une heure au format HH:MM, retourne l'objet time ou None."""
    if not heure_str:
        return None, None
    try:
        return datetime.strptime(heure_str, '%H:%M').time(), None
    except ValueError:
        return None, "Format d'heure invalide. Utilisez HH:MM"


def parse_duree(duree_str):
    """Parse et valide une durée entière >= 1."""
    try:
        d = int(duree_str)
        return max(d, 1)
    except (ValueError, TypeError):
        return 1


# ─────────────────────────────────────────────
#  ROUTE FRANÇAISE
# ─────────────────────────────────────────────


@matiere_bp.route('/add_matiere/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_matiere(classe_id):
    classe   = Classe.query.get_or_404(classe_id)
    ecole_id = session['ecole_id']
 
    if classe.ecole_id != ecole_id:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))
 
    if request.method == 'POST':
        action = request.form.get('action')
 
        if action in ['add', 'edit']:
            nom        = request.form.get('nom', '').strip()
            # ── Le champ professeur vient maintenant du champ caché ──
            professeur = request.form.get('professeur', '').strip() or None
            jour       = request.form.get('jour', '').strip()
            heure_str  = request.form.get('heure', '').strip()
            duree      = request.form.get('duree', '1')
 
            if not nom or not jour or not heure_str:
                flash("Le nom, le jour et l'heure sont obligatoires.", "error")
                return redirect(url_for('matiere.add_matiere', classe_id=classe_id))
 
            try:
                from datetime import time as time_type
                h, m = map(int, heure_str.split(':'))
                heure = time_type(h, m)
            except Exception:
                flash("Format d'heure invalide.", "error")
                return redirect(url_for('matiere.add_matiere', classe_id=classe_id))
 
            if action == 'add':
                matiere = Matiere(
                    nom=nom,
                    professeur=professeur,
                    jour=jour,
                    heure=heure,
                    duree=float(duree),
                    classe_id=classe_id
                )
                db.session.add(matiere)
                db.session.commit()
                flash(f"Matière '{nom}' ajoutée.", "success")
 
            elif action == 'edit':
                matiere_id = request.form.get('matiere_id')
                matiere    = Matiere.query.get_or_404(matiere_id)

                if matiere.classe_id != classe_id:
                   flash("Action non autorisée.", "error")
                   return redirect(url_for('matiere.add_matiere', classe_id=classe_id))

    # ── FIX : supprimer les affectations liées avant modification ──
                from models import ProfesseurAffectation
                ProfesseurAffectation.query.filter_by(matiere_id=matiere.id).delete(synchronize_session=False)

                matiere.nom        = nom
                matiere.professeur = professeur
                matiere.jour       = jour
                matiere.heure      = heure
                matiere.duree      = float(duree)
                db.session.commit()
                flash(f"Matière '{nom}' mise à jour.", "success")
 
        elif action == 'delete':
            matiere_id = request.form.get('matiere_id')
            matiere    = Matiere.query.get_or_404(matiere_id)

            from models import ProfesseurAffectation
    # ── FIX : supprimer d'abord les affectations ──
            ProfesseurAffectation.query.filter_by(matiere_id=matiere.id).delete(synchronize_session=False)
            Note.query.filter_by(matiere_id=matiere.id).delete(synchronize_session=False)
            db.session.delete(matiere)
            db.session.commit()
            flash(f"Matière supprimée.", "success")
 
        return redirect(url_for('matiere.add_matiere', classe_id=classe_id))
 
    # ── GET ──────────────────────────────────────────────────────
    matieres = Matiere.query.filter_by(classe_id=classe_id)\
                            .order_by(Matiere.jour, Matiere.heure).all()
 
    # ── Professeurs enregistrés pour cette école ← NOUVEAU ──────
    professeurs = Professeur.query.filter_by(
        ecole_id=ecole_id,
        actif=True
    ).order_by(Professeur.nom, Professeur.prenom).all()
 
    # Ajouter nom_complet si pas déjà défini comme property
    for p in professeurs:
        if not hasattr(p, '_nom_complet_cache'):
            p._nom_complet = f"{p.prenom} {p.nom}"
 
    return render_template(
        'add_matiere.html',
        classe=classe,
        matieres=matieres,
        professeurs=professeurs,     # ← NOUVEAU
    )

# ─────────────────────────────────────────────
#  ROUTE FRANCO-ARABE
# ─────────────────────────────────────────────

@matiere_bp.route('/add_matiere_ar/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_matiere_ar(classe_id):
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé à cette page.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard_ar'))

    if request.method == 'POST':
        action     = request.form.get('action')
        matiere_id = request.form.get('matiere_id')

        try:
            # ── ADD ──────────────────────────────────────
            if action == 'add':
                nom        = request.form.get('nom', '').strip()
                professeur = request.form.get('professeur', '').strip() or None
                jour       = request.form.get('jour') or None
                heure_str  = request.form.get('heure')
                duree      = parse_duree(request.form.get('duree', '1'))

                if not nom:
                    flash("اسم المادة إلزامي.", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                heure_obj, err = parse_heure(heure_str, None)
                if err:
                    flash("صيغة الساعة غير صحيحة. استخدم HH:MM", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                # ✅ Vérification conflit horaire uniquement
                conflit, mat_conflit = check_horaire_conflict(classe_id, jour, heure_obj, duree)
                if conflit:
                    heure_fmt = mat_conflit.heure.strftime('%H:%M') if mat_conflit.heure else ''
                    flash(
                        f"تعارض في الجدول: المادة '{mat_conflit.nom}' تشغل هذا الوقت "
                        f"يوم {jour} الساعة {heure_fmt}.",
                        "warning"
                    )
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                db.session.add(Matiere(
                    nom=nom, classe_id=classe_id, professeur=professeur,
                    jour=jour, heure=heure_obj, duree=duree
                ))
                db.session.commit()
                flash(f"تمت إضافة المادة '{nom}' بنجاح.", "success")

            # ── EDIT ─────────────────────────────────────
            elif action == 'edit' and matiere_id:
                matiere = Matiere.query.get_or_404(matiere_id)

                if matiere.classe_id != classe_id:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                nom        = request.form.get('nom', '').strip()
                professeur = request.form.get('professeur', '').strip() or None
                jour       = request.form.get('jour') or None
                heure_str  = request.form.get('heure')
                duree      = parse_duree(request.form.get('duree', '1'))

                if not nom:
                    flash("اسم المادة إلزامي.", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                heure_obj, err = parse_heure(heure_str, None)
                if err:
                    flash("صيغة الساعة غير صحيحة. استخدم HH:MM", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                # ✅ Conflit horaire en excluant la matière en cours d'édition
                conflit, mat_conflit = check_horaire_conflict(
                    classe_id, jour, heure_obj, duree, exclude_id=matiere.id
                )
                if conflit:
                    heure_fmt = mat_conflit.heure.strftime('%H:%M') if mat_conflit.heure else ''
                    flash(
                        f"تعارض في الجدول: المادة '{mat_conflit.nom}' تشغل هذا الوقت "
                        f"يوم {jour} الساعة {heure_fmt}.",
                        "warning"
                    )
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                matiere.nom        = nom
                matiere.professeur = professeur
                matiere.jour       = jour
                matiere.heure      = heure_obj
                matiere.duree      = duree
                db.session.commit()
                flash(f"تم تعديل المادة '{nom}'.", "success")

            # ── DELETE ───────────────────────────────────
            elif action == 'delete' and matiere_id:
                matiere = Matiere.query.get_or_404(matiere_id)

                if matiere.classe_id != classe_id:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

                nom      = matiere.nom
                nb_notes = Note.query.filter_by(matiere_id=matiere.id).count()
                Note.query.filter_by(matiere_id=matiere_id).delete()
                db.session.delete(matiere)
                db.session.commit()
                flash(f"تم حذف المادة '{nom}' مع {nb_notes} نقطة(ات).", "success")

            return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

        except Exception as e:
            db.session.rollback()
            flash("حدث خطأ أثناء المعالجة.", "error")
            return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))

    # ── GET ──────────────────────────────────────────────
    matieres = Matiere.query.filter_by(classe_id=classe_id).order_by(Matiere.jour, Matiere.heure).all()
    for m in matieres:
        m.nb_notes = Note.query.filter_by(matiere_id=m.id).count()

    return render_template('add_matiere_ar.html', classe=classe, matieres=matieres)
