from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Classe, Eleve, Note, Ecole, MatriculeUsed
from utils import login_required
from datetime import date, datetime
import traceback
import uuid
import os
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'webp'}

eleve_bp = Blueprint('eleve', __name__, url_prefix='/ecole')


# ─────────────────────────────────────────────
#  UPLOAD PHOTO → SUPABASE STORAGE
# ─────────────────────────────────────────────

def save_photo(file):
    """
    Upload la photo vers Supabase Storage.
    Fallback : sauvegarde locale si Supabase non configuré.
    """
    if not file or file.filename == '':
        return None

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return None

    filename = f"photos/{uuid.uuid4().hex}.{ext}"

    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')

    # ── Supabase Storage ──────────────────────────────────────
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)

            file_bytes   = file.read()
            content_type = file.content_type or f'image/{ext}'
            bucket       = os.environ.get('SUPABASE_BUCKET', 'eleves')

            supabase.storage.from_(bucket).upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            public_url = supabase.storage.from_(bucket).get_public_url(filename)
            print(f"✅ Photo uploadée Supabase : {public_url}")
            return public_url

        except Exception as e:
            print(f"❌ Erreur upload Supabase Storage : {e}")
            # Fallback local si l'upload échoue
            return _save_photo_local(file, filename, ext)

    # ── Fallback local (développement) ───────────────────────
    return _save_photo_local(file, filename, ext)


def _save_photo_local(file, filename, ext):
    """Sauvegarde locale en fallback"""
    try:
        # Rembobiner si déjà lu par Supabase
        if hasattr(file, 'seek'):
            file.seek(0)
        local_name   = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/photos')
        os.makedirs(upload_folder, exist_ok=True)
        path = os.path.join(upload_folder, local_name)
        file.save(path)
        return f"/static/uploads/photos/{local_name}"
    except Exception as e:
        print(f"❌ Erreur sauvegarde locale : {e}")
        return None


# ─────────────────────────────────────────────
#  UTILITAIRES MATRICULE (scopés par école)
# ─────────────────────────────────────────────

def generate_matricule(ecole_id):
    last = db.session.query(
        db.func.max(db.cast(MatriculeUsed.matricule, db.Integer))
    ).filter(MatriculeUsed.ecole_id == ecole_id).scalar()
    next_num = 1001 if last is None else last + 1
    return str(next_num)


def reserve_matricule(matricule, ecole_id):
    exists = MatriculeUsed.query.filter_by(
        matricule=matricule,
        ecole_id=ecole_id
    ).first()
    if not exists:
        db.session.add(MatriculeUsed(matricule=matricule, ecole_id=ecole_id))


def validate_matricule(matricule, ecole_id, exclude_eleve_id=None):
    matricule = matricule.strip()
    if not matricule:
        return False, "Le matricule est obligatoire."

    query = db.session.query(Eleve).join(Classe).filter(
        Classe.ecole_id == ecole_id,
        Eleve.matricule == matricule
    )
    if exclude_eleve_id:
        query = query.filter(Eleve.id != int(exclude_eleve_id))
    if query.first():
        return False, f"Le matricule {matricule} est déjà utilisé dans votre établissement."

    if MatriculeUsed.query.filter_by(matricule=matricule, ecole_id=ecole_id).first():
        return False, (
            f"Le matricule {matricule} a déjà été attribué dans votre établissement "
            f"et ne peut pas être réutilisé."
        )
    return True, None


# ─────────────────────────────────────────────
#  HELPER SUPPRESSION COMPLÈTE D'UN ÉLÈVE
# ─────────────────────────────────────────────

def supprimer_eleve_complet(eleve):
    """
    Supprime un élève et TOUTES ses données liées via SQL direct
    pour éviter les problèmes de backref/autoflush.
    """
    from models import Scolarite, Paiement, Absence, BulletinVerification

    eid = eleve.id

    # SQL direct — bypass tous les backrefs SQLAlchemy
    db.session.execute(db.text("DELETE FROM absence             WHERE eleve_id    = :id"), {"id": eid})
    db.session.execute(db.text("DELETE FROM bulletin_verification WHERE eleve_id  = :id"), {"id": eid})
    db.session.execute(db.text("DELETE FROM note                WHERE eleve_id    = :id"), {"id": eid})
    db.session.execute(db.text("""
        DELETE FROM paiement WHERE scolarite_id IN
        (SELECT id FROM scolarite WHERE eleve_id = :id)
    """), {"id": eid})
    db.session.execute(db.text("DELETE FROM scolarite           WHERE eleve_id    = :id"), {"id": eid})
    db.session.execute(db.text("DELETE FROM eleve               WHERE id          = :id"), {"id": eid})


# ─────────────────────────────────────────────
#  ROUTE FRANÇAISE
# ─────────────────────────────────────────────

@eleve_bp.route('/add_eleve/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_eleve(classe_id):
    classe = Classe.query.get_or_404(classe_id)
    ecole_id = session.get('ecole_id')

    # Vérification des droits d'accès
    if classe.ecole_id != ecole_id:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            # --- ACTION: AJOUTER OU MODIFIER ---
            if action in ['add', 'edit']:
                eleve_id = request.form.get('eleve_id')
                prenom = request.form.get('prenom', '').strip()
                nom = request.form.get('nom', '').strip()
                matricule = request.form.get('matricule', '').strip()
                tuteur = request.form.get('tuteur', '').strip() or None
                telephone_tuteur = request.form.get('telephone_tuteur', '').strip() or None

                if not prenom or not nom:
                    flash("Le prénom et le nom sont obligatoires.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                # Parsing de la date
                try:
                    date_naissance_str = request.form.get('date_naissance', '')
                    date_naissance = date.fromisoformat(date_naissance_str) if date_naissance_str else None
                except ValueError:
                    flash("Format de date invalide. Utilisez AAAA-MM-JJ.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                # Genre / Sexe
                sexe = request.form.get('sexe', '')
                if sexe not in ['M', 'F']:
                    sexe = None

                # Génération auto si matricule vide
                if not matricule:
                    matricule = generate_matricule(ecole_id)

                # Validation du matricule
                is_same = False
                if action == 'edit' and eleve_id:
                    current = db.session.get(Eleve, eleve_id)
                    if current and current.matricule == matricule:
                        is_same = True

                if not is_same:
                    ok, err = validate_matricule(matricule, ecole_id, exclude_eleve_id=eleve_id)
                    if not ok:
                        flash(err, "warning")
                        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                # Création
                if action == 'add':
                    photo_url = save_photo(request.files.get('photo'))
                    eleve = Eleve(
                        prenom=prenom, nom=nom, matricule=matricule,
                        date_naissance=date_naissance, sexe=sexe,
                        tuteur=tuteur, telephone_tuteur=telephone_tuteur,
                        classe_id=classe_id, photo_url=photo_url
                    )
                    db.session.add(eleve)
                    reserve_matricule(matricule, ecole_id)
                    db.session.commit()
                    flash(f"Élève {prenom} {nom} ajouté avec le matricule {matricule}.", "success")

                # Modification
                elif action == 'edit' and eleve_id:
                    eleve = Eleve.query.get_or_404(eleve_id)
                    if eleve.classe_id != classe_id:
                        flash("Action non autorisée.", "error")
                        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))
                    
                    if eleve.matricule != matricule:
                        reserve_matricule(matricule, ecole_id)
                    
                    photo_url = save_photo(request.files.get('photo'))
                    eleve.photo_url = photo_url or eleve.photo_url
                    eleve.prenom = prenom
                    eleve.nom = nom
                    eleve.matricule = matricule
                    eleve.date_naissance = date_naissance
                    eleve.sexe = sexe
                    eleve.tuteur = tuteur
                    eleve.telephone_tuteur = telephone_tuteur
                    
                    db.session.commit()
                    flash(f"Informations de {prenom} {nom} ({matricule}) mises à jour.", "success")

            # --- ACTION: ARCHIVER UN ÉLÈVE ---
            elif action == 'archive' and request.form.get('eleve_id'):
                eleve = Eleve.query.get_or_404(request.form['eleve_id'])

                if eleve.classe_id != classe_id:
                    flash("Action non autorisée.", "error")
                    return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

                nom_complet = f"{eleve.prenom} {eleve.nom}"
                motif = request.form.get('motif_archive', '').strip() or None

                eleve.archive = True
                eleve.date_archive = datetime.utcnow()
                eleve.motif_archive = motif
                db.session.commit()

                flash(
                    f"Élève {nom_complet} archivé. Ses données sont conservées dans l'archive.",
                    "success"
                )

            # --- ACTION: ARCHIVER TOUTE LA CLASSE ---
            elif action == 'archive_all':
                eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
                count = len(eleves)
                motif = request.form.get('motif_archive', '').strip() or None
                now = datetime.utcnow()

                for eleve in eleves:
                    eleve.archive = True
                    eleve.date_archive = now
                    eleve.motif_archive = motif

                db.session.commit()
                flash(f"{count} élève(s) archivé(s). Leurs données sont conservées.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "error")
            flash(traceback.format_exc(), "error")

        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

    # --- MÉTHODE GET ---
    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).order_by(Eleve.nom, Eleve.prenom).all()
    for eleve in eleves:
        eleve.nb_notes = Note.query.filter_by(eleve_id=eleve.id).count()
        
    suggested_matricule = generate_matricule(ecole_id)

    return render_template(
        'add_eleve.html',
        classe=classe, 
        eleves=eleves, 
        suggested_matricule=suggested_matricule
    )




# ─────────────────────────────────────────────
#  ROUTE ARABE
# ─────────────────────────────────────────────

@eleve_bp.route('/add_eleve_ar/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def add_eleve_ar(classe_id):
    ecole    = Ecole.query.get(session['ecole_id'])
    classe   = Classe.query.get_or_404(classe_id)
    ecole_id = session['ecole_id']

    if classe.ecole_id != ecole_id:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard_ar'))

    if request.method == 'POST':
        action = request.form.get('action')

        try:
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
                    flash("صيغة التاريخ غير صحيحة.", "error")
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

                if action == 'add':
                    photo_url = save_photo(request.files.get('photo'))
                    eleve = Eleve(
                        prenom=prenom, nom=nom, matricule=matricule,
                        date_naissance=date_naissance, sexe=sexe,
                        tuteur=tuteur, telephone_tuteur=telephone_tuteur,
                        classe_id=classe_id, photo_url=photo_url
                    )
                    db.session.add(eleve)
                    reserve_matricule(matricule, ecole_id)
                    db.session.commit()
                    flash(f"تمت إضافة التلميذ {prenom} {nom} برقم تسجيل {matricule}.", "success")

                elif action == 'edit' and eleve_id:
                    eleve = Eleve.query.get_or_404(eleve_id)
                    if eleve.classe_id != classe_id:
                        flash("إجراء غير مصرح به.", "error")
                        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))
                    if eleve.matricule != matricule:
                        reserve_matricule(matricule, ecole_id)
                    photo_url = save_photo(request.files.get('photo'))
                    eleve.photo_url        = photo_url or eleve.photo_url
                    eleve.prenom           = prenom
                    eleve.nom              = nom
                    eleve.matricule        = matricule
                    eleve.date_naissance   = date_naissance
                    eleve.sexe             = sexe
                    eleve.tuteur           = tuteur
                    eleve.telephone_tuteur = telephone_tuteur
                    db.session.commit()
                    flash(f"تم تحديث معلومات {prenom} {nom} ({matricule}).", "success")

            # ── DELETE un élève ── correctement avec supprimer_eleve_complet
            elif action == 'delete' and request.form.get('eleve_id'):
                eleve = Eleve.query.get_or_404(request.form['eleve_id'])
                if eleve.classe_id != classe_id:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))
                nom_complet = f"{eleve.prenom} {eleve.nom}"
                mat         = eleve.matricule
                supprimer_eleve_complet(eleve)
                db.session.commit()
                flash(f"تم حذف التلميذ {nom_complet}. رقم التسجيل {mat} محجوز نهائياً.", "success")

            # ── DELETE ALL ── correctement avec supprimer_eleve_complet#
            elif action == 'delete_all':
                eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
                count  = len(eleves)
                for eleve in eleves:
                    supprimer_eleve_complet(eleve)
                db.session.commit()
                flash(f"تم حذف {count} تلميذ(ة). أرقام تسجيلهم محجوزة نهائياً.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "error")
            flash(traceback.format_exc(), "error")

        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).order_by(Eleve.nom, Eleve.prenom).all()
    for eleve in eleves:
        eleve.nb_notes = Note.query.filter_by(eleve_id=eleve.id).count()
    suggested_matricule = generate_matricule(ecole_id)

    return render_template('add_eleve_ar.html',
        classe=classe, eleves=eleves, suggested_matricule=suggested_matricule)


#  2. Nouvelle route — Page archives
# ══════════════════════════════════════════════════════════════
 
@eleve_bp.route('/archives', methods=['GET'])
@login_required
def archives_eleves():
    """Page archive : tous les élèves archivés de l'école"""
    from models import Classe
    ecole_id = session['ecole_id']
 
    # Filtres
    classe_id_filter  = request.args.get('classe_id', type=int)
    annee_filter      = request.args.get('annee', '').strip()
    search            = request.args.get('q', '').strip().lower()
 
    # Récupérer toutes les classes de l'école
    classes = Classe.query.filter_by(ecole_id=ecole_id)\
                          .order_by(Classe.annee_scolaire.desc(), Classe.nom).all()
 
    # Requête de base : élèves archivés de cette école
    query = db.session.query(Eleve)\
                      .join(Classe)\
                      .filter(
                          Classe.ecole_id == ecole_id,
                          Eleve.archive   == True
                      )
 
    if classe_id_filter:
        query = query.filter(Eleve.classe_id == classe_id_filter)
 
    if annee_filter:
        query = query.filter(Classe.annee_scolaire == annee_filter)
 
    if search:
        query = query.filter(
            db.or_(
                Eleve.prenom.ilike(f'%{search}%'),
                Eleve.nom.ilike(f'%{search}%'),
                Eleve.matricule.ilike(f'%{search}%'),
            )
        )
 
    eleves_archives = query.order_by(Eleve.date_archive.desc()).all()
 
    # Années disponibles pour le filtre
    annees = db.session.query(Classe.annee_scolaire)\
                       .filter(Classe.ecole_id == ecole_id)\
                       .distinct()\
                       .order_by(Classe.annee_scolaire.desc())\
                       .all()
    annees = [a[0] for a in annees]
 
    return render_template('archives_eleves.html',
        eleves_archives=eleves_archives,
        classes=classes,
        annees=annees,
        classe_id_filter=classe_id_filter,
        annee_filter=annee_filter,
        search=search,
    )
 
 
# ══════════════════════════════════════════════════════════════
#  3. Route — Restaurer un élève archivé
# ══════════════════════════════════════════════════════════════
 
@eleve_bp.route('/archives/restaurer/<int:eleve_id>', methods=['POST'])
@login_required
def restaurer_eleve(eleve_id):
    """Restaure un élève archivé vers sa classe d'origine"""
    ecole_id = session['ecole_id']
    eleve    = Eleve.query.get_or_404(eleve_id)
    classe   = Classe.query.get(eleve.classe_id)
 
    if not classe or classe.ecole_id != ecole_id:
        flash("Action non autorisée.", "error")
        return redirect(url_for('eleve.archives_eleves'))
 
    eleve.archive       = False
    eleve.date_archive  = None
    eleve.motif_archive = None
    db.session.commit()
 
    flash(f"Élève {eleve.prenom} {eleve.nom} restauré dans {classe.nom}.", "success")
    return redirect(url_for('eleve.archives_eleves'))
 
 
# ══════════════════════════════════════════════════════════════
#  4. Route — Supprimer définitivement (depuis les archives)
# ══════════════════════════════════════════════════════════════
 
@eleve_bp.route('/archives/supprimer/<int:eleve_id>', methods=['POST'])
@login_required
def supprimer_archive(eleve_id):
    """Suppression définitive depuis les archives"""
    ecole_id = session['ecole_id']
    eleve    = Eleve.query.get_or_404(eleve_id)
    classe   = Classe.query.get(eleve.classe_id)
 
    if not classe or classe.ecole_id != ecole_id:
        flash("Action non autorisée.", "error")
        return redirect(url_for('eleve.archives_eleves'))
 
    if not eleve.archive:
        flash("Cet élève n'est pas archivé.", "warning")
        return redirect(url_for('eleve.archives_eleves'))
 
    nom = f"{eleve.prenom} {eleve.nom}"
    supprimer_eleve_complet(eleve)
    db.session.commit()
 
    flash(f"Élève {nom} supprimé définitivement.", "success")
    return redirect(url_for('eleve.archives_eleves'))
 