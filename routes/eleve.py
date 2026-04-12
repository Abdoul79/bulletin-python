from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Classe, Eleve, Note, Ecole, MatriculeUsed
from utils import login_required
from datetime import date, datetime
import traceback
import uuid;
import os
from werkzeug.utils import secure_filename
from flask import current_app

UPLOAD_FOLDER = 'static/uploads/photos'
ALLOWED_EXT   = {'jpg', 'jpeg', 'png', 'webp'}

eleve_bp = Blueprint('eleve', __name__, url_prefix='/ecole')


# ─────────────────────────────────────────────
#  UTILITAIRES MATRICULE (scopés par école)
# ─────────────────────────────────────────────

def generate_matricule(ecole_id):
    """
    Génère le prochain matricule pour une école donnée.
    Commence à 1001 et incrémente à partir du MAX de cette école.
    Deux écoles différentes peuvent avoir les mêmes numéros.
    """
    last = db.session.query(
        db.func.max(db.cast(MatriculeUsed.matricule, db.Integer))
    ).filter(MatriculeUsed.ecole_id == ecole_id).scalar()

    next_num = 1001 if last is None else last + 1
    return str(next_num)


def reserve_matricule(matricule, ecole_id):
    """
    Enregistre le matricule dans MatriculeUsed pour cette école.
    Jamais réattribué au sein du même établissement.
    """
    exists = MatriculeUsed.query.filter_by(
        matricule=matricule,
        ecole_id=ecole_id
    ).first()
    if not exists:
        db.session.add(MatriculeUsed(matricule=matricule, ecole_id=ecole_id))


def validate_matricule(matricule, ecole_id, exclude_eleve_id=None):
    """
    Vérifie que le matricule est valide pour cette école uniquement.
    D'autres écoles peuvent avoir le même numéro — c'est normal.
    """
    matricule = matricule.strip()
    if not matricule:
        return False, "Le matricule est obligatoire."

    # Vérifier parmi les élèves actifs de la même école
    query = db.session.query(Eleve).join(Classe).filter(
        Classe.ecole_id == ecole_id,
        Eleve.matricule == matricule
    )
    if exclude_eleve_id:
        query = query.filter(Eleve.id != int(exclude_eleve_id))
    if query.first():
        return False, f"Le matricule {matricule} est déjà utilisé dans votre établissement."

    # Vérifier dans l'historique de cette école
    if MatriculeUsed.query.filter_by(matricule=matricule, ecole_id=ecole_id).first():
        return False, (
            f"Le matricule {matricule} a déjà été attribué dans votre établissement "
            f"et ne peut pas être réutilisé."
        )

    return True, None


# ─────────────────────────────────────────────
#  ROUTE FRANÇAISE
# ─────────────────────────────────────────────
@eleve_bp.route('/add_eleve/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_eleve(classe_id):
    classe   = Classe.query.get_or_404(classe_id)
    ecole_id = session['ecole_id']

    if classe.ecole_id != ecole_id:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    # ── Helper : suppression complète d'un élève ─────────────────
    def supprimer_eleve_complet(eleve):
        """Supprime un élève et toutes ses données liées dans le bon ordre :
           Paiements → Scolarités → Notes → Élève"""
        from models import Scolarite, Paiement
        # 1. Paiements et scolarités
        for scolarite in Scolarite.query.filter_by(eleve_id=eleve.id).all():
            Paiement.query.filter_by(scolarite_id=scolarite.id).delete(synchronize_session=False)
            db.session.delete(scolarite)
        # 2. Notes
        Note.query.filter_by(eleve_id=eleve.id).delete(synchronize_session=False)
        # 3. Élève
        db.session.delete(eleve)

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            # ── ADD / EDIT ────────────────────────────────────────
            if action in ['add', 'edit']:
                eleve_id         = request.form.get('eleve_id')
                prenom           = request.form.get('prenom', '').strip()
                nom              = request.form.get('nom', '').strip()
                matricule        = request.form.get('matricule', '').strip()
                tuteur           = request.form.get('tuteur', '').strip() or None
                telephone_tuteur = request.form.get('telephone_tuteur', '').strip() or None

                if not prenom or not nom:
                    flash("Le prénom et le nom sont obligatoires.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                try:
                    date_naissance_str = request.form.get('date_naissance', '')
                    date_naissance = date.fromisoformat(date_naissance_str) if date_naissance_str else None
                except ValueError:
                    flash("Format de date invalide. Utilisez AAAA-MM-JJ.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                sexe = request.form.get('sexe', '')
                if sexe not in ['M', 'F']:
                    sexe = None

                # Générer si vide
                if not matricule:
                    matricule = generate_matricule(ecole_id)

                # En mode edit, pas de revalidation si même matricule
                is_same = False
                if action == 'edit' and eleve_id:
                    current = Eleve.query.get(eleve_id)
                    if current and current.matricule == matricule:
                        is_same = True

                if not is_same:
                    ok, err = validate_matricule(matricule, ecole_id, exclude_eleve_id=eleve_id)
                    if not ok:
                        flash(err, "warning")
                        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                # ── ADD ──────────────────────────────────────────
                if action == 'add':
                    photo_url = save_photo(request.files.get('photo'))
                    eleve = Eleve(
                        prenom=prenom,
                        nom=nom,
                        matricule=matricule,
                        date_naissance=date_naissance,
                        sexe=sexe,
                        tuteur=tuteur,
                        telephone_tuteur=telephone_tuteur,
                        classe_id=classe_id,
                        photo_url=photo_url
                    )
                    db.session.add(eleve)
                    reserve_matricule(matricule, ecole_id)
                    db.session.commit()
                    flash(f"Élève {prenom} {nom} ajouté avec le matricule {matricule}.", "success")

                # ── EDIT ─────────────────────────────────────────
                elif action == 'edit' and eleve_id:
                    eleve = Eleve.query.get_or_404(eleve_id)

                    if eleve.classe_id != classe_id:
                        flash("Action non autorisée.", "error")
                        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                    if eleve.matricule != matricule:
                        reserve_matricule(matricule, ecole_id)

                    # Gestion photo (garder l'ancienne si pas de nouvelle)
                    photo_url = save_photo(request.files.get('photo'))
                    eleve.photo_url = photo_url or eleve.photo_url

                    eleve.prenom           = prenom
                    eleve.nom              = nom
                    eleve.matricule        = matricule
                    eleve.date_naissance   = date_naissance
                    eleve.sexe             = sexe
                    eleve.tuteur           = tuteur
                    eleve.telephone_tuteur = telephone_tuteur
                    db.session.commit()
                    flash(f"Informations de {prenom} {nom} ({matricule}) mises à jour.", "success")

            # ── DELETE (un seul élève) ────────────────────────────
            elif action == 'delete' and request.form.get('eleve_id'):
                eleve = Eleve.query.get_or_404(request.form['eleve_id'])

                if eleve.classe_id != classe_id:
                    flash("Action non autorisée.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                nom_complet = f"{eleve.prenom} {eleve.nom}"
                mat         = eleve.matricule

                supprimer_eleve_complet(eleve)
                db.session.commit()

                flash(
                    f"Élève {nom_complet} supprimé. "
                    f"Le matricule {mat} est définitivement réservé dans votre établissement.",
                    "success"
                )

            # ── DELETE ALL ────────────────────────────────────────
            elif action == 'delete_all':
                eleves = Eleve.query.filter_by(classe_id=classe_id).all()
                count  = len(eleves)

                for eleve in eleves:
                    supprimer_eleve_complet(eleve)

                db.session.commit()
                flash(
                    f"{count} élève(s) supprimé(s). "
                    f"Leurs matricules sont définitivement réservés dans votre établissement.",
                    "success"
                )

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "error")
            flash(traceback.format_exc(), "error")

        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

    # ── GET ───────────────────────────────────────────────────────
    eleves = Eleve.query.filter_by(classe_id=classe_id).order_by(Eleve.nom, Eleve.prenom).all()
    for eleve in eleves:
        eleve.nb_notes = Note.query.filter_by(eleve_id=eleve.id).count()

    suggested_matricule = generate_matricule(ecole_id)

    return render_template(
        'add_eleve.html',
        classe=classe,
        eleves=eleves,
        suggested_matricule=suggested_matricule
    )



def save_photo(file):
    if not file or file.filename == '':
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)
    return f"/{UPLOAD_FOLDER}/{filename}"




# ─────────────────────────────────────────────
#  ROUTE FRANCO-ARABE
# ─────────────────────────────────────────────

@eleve_bp.route('/add_eleve_ar/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_eleve_ar(classe_id):
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    classe   = Classe.query.get_or_404(classe_id)
    ecole_id = session['ecole_id']

    if classe.ecole_id != ecole_id:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard_ar'))

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            # ── ADD / EDIT ────────────────────────────────
            if action in ['add', 'edit']:
                eleve_id         = request.form.get('eleve_id')
                prenom           = request.form.get('prenom', '').strip()
                nom              = request.form.get('nom', '').strip()
                matricule        = request.form.get('matricule', '').strip()
                tuteur           = request.form.get('tuteur', '').strip() or None
                telephone_tuteur = request.form.get('telephone_tuteur', '').strip() or None

                if not prenom or not nom:
                    flash("الاسم واللقب إلزاميان.", "error")
                    return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

                try:
                    date_naissance_str = request.form.get('date_naissance', '')
                    date_naissance = date.fromisoformat(date_naissance_str) if date_naissance_str else None
                except ValueError:
                    flash("صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD.", "error")
                    return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

                sexe = request.form.get('sexe', '')
                if sexe not in ['M', 'F']:
                    sexe = None

                if not matricule:
                    matricule = generate_matricule(ecole_id)

                is_same = False
                if action == 'edit' and eleve_id:
                    current = Eleve.query.get(eleve_id)
                    if current and current.matricule == matricule:
                        is_same = True

                if not is_same:
                    ok, err = validate_matricule(matricule, ecole_id, exclude_eleve_id=eleve_id)
                    if not ok:
                        flash(f"رقم التسجيل غير صالح: {err}", "warning")
                        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

                # ── ADD ──────────────────────────────────
                if action == 'add':
                    photo_url = save_photo(request.files.get('photo'))
                    eleve = Eleve(
                        prenom=prenom,
                        nom=nom,
                        matricule=matricule,
                        date_naissance=date_naissance,
                        sexe=sexe,
                        tuteur=tuteur,
                        telephone_tuteur=telephone_tuteur,
                        classe_id=classe_id,
                        photo_url=photo_url
                    )
                    db.session.add(eleve)
                    reserve_matricule(matricule, ecole_id)
                    db.session.commit()
                    flash(f"تمت إضافة التلميذ {prenom} {nom} برقم تسجيل {matricule}.", "success")

                # ── EDIT ─────────────────────────────────
                elif action == 'edit' and eleve_id:
                    eleve = Eleve.query.get_or_404(eleve_id)

                    if eleve.classe_id != classe_id:
                        flash("إجراء غير مصرح به.", "error")
                        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

                    if eleve.matricule != matricule:
                        reserve_matricule(matricule, ecole_id)

                    photo_url = save_photo(request.files.get('photo'))
                    eleve.photo_url = photo_url or eleve.photo_url

                    eleve.prenom           = prenom
                    eleve.nom              = nom
                    eleve.matricule        = matricule
                    eleve.date_naissance   = date_naissance
                    eleve.sexe             = sexe
                    eleve.tuteur           = tuteur
                    eleve.telephone_tuteur = telephone_tuteur
                    db.session.commit()
                    flash(f"تم تحديث معلومات {prenom} {nom} ({matricule}).", "success")

            # ── DELETE ───────────────────────────────────
            elif action == 'delete' and request.form.get('eleve_id'):
                eleve = Eleve.query.get_or_404(request.form['eleve_id'])

                if eleve.classe_id != classe_id:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

                nom_complet = f"{eleve.prenom} {eleve.nom}"
                mat         = eleve.matricule
                nb_notes    = Note.query.filter_by(eleve_id=eleve.id).count()
                if nb_notes > 0:
                    Note.query.filter_by(eleve_id=eleve.id).delete()
                db.session.delete(eleve)
                db.session.commit()
                flash(
                    f"تم حذف التلميذ {nom_complet}. "
                    f"رقم التسجيل {mat} محجوز نهائياً في مؤسستك.",
                    "success"
                )

            # ── DELETE ALL ───────────────────────────────
            elif action == 'delete_all':
                eleves     = Eleve.query.filter_by(classe_id=classe_id).all()
                eleves_ids = [e.id for e in eleves]
                if eleves_ids:
                    Note.query.filter(
                        Note.eleve_id.in_(eleves_ids)
                    ).delete(synchronize_session=False)
                count = len(eleves)
                Eleve.query.filter_by(classe_id=classe_id).delete()
                db.session.commit()
                flash(
                    f"تم حذف {count} تلميذ(ة). "
                    f"أرقام تسجيلهم محجوزة نهائياً في مؤسستك.",
                    "success"
                )

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "error")
            flash(traceback.format_exc(), "error")

        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

    # ── GET ──────────────────────────────────────────────
    eleves = Eleve.query.filter_by(classe_id=classe_id).order_by(Eleve.nom, Eleve.prenom).all()
    for eleve in eleves:
        eleve.nb_notes = Note.query.filter_by(eleve_id=eleve.id).count()

    suggested_matricule = generate_matricule(ecole_id)

    return render_template(
        'add_eleve_ar.html',
        classe=classe,
        eleves=eleves,
        suggested_matricule=suggested_matricule
    )
