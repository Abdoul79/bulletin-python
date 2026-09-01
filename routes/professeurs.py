"""
routes/professeurs.py
Blueprint gestion des professeurs + authentification professeur
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from models import db, Ecole, Classe, Matiere, Professeur, ProfesseurAffectation, Note, Eleve
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

professeurs_bp = Blueprint('professeurs', __name__)


# ── Décorateurs ──────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'ecole_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def prof_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'professeur_id' not in session:
            return redirect(url_for('professeurs.prof_login'))
        return f(*args, **kwargs)
    return decorated


# ════════════════════════════════════════════════════════════════
#  SECTION ÉCOLE — Gérer les professeurs
# ════════════════════════════════════════════════════════════════

@professeurs_bp.route('/professeurs', methods=['GET', 'POST'])
@login_required
def gerer_professeurs():
    """Page de gestion des professeurs (accessible à l'école)"""
    ecole    = Ecole.query.get(session['ecole_id'])
    classes  = Classe.query.filter_by(ecole_id=ecole.id).all()
    profs    = Professeur.query.filter_by(ecole_id=ecole.id).order_by(Professeur.nom).all()

    if request.method == 'POST':
        action = request.form.get('action')

        # ── Ajouter un professeur ──
        if action == 'add':
            nom      = request.form.get('nom', '').strip()
            prenom   = request.form.get('prenom', '').strip()
            email    = request.form.get('email', '').strip().lower()
            tel      = request.form.get('telephone', '').strip() or None
            password = request.form.get('password', '').strip()

            if not nom or not prenom or not email or not password:
                flash("Tous les champs obligatoires doivent être remplis.", "error")
            elif len(password) < 6:
                flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            elif Professeur.query.filter_by(email=email).first():
                flash(f"L'email {email} est déjà utilisé.", "error")
            else:
                prof = Professeur(
                    ecole_id=ecole.id,
                    nom=nom, prenom=prenom,
                    email=email, telephone=tel,
                    mot_de_passe=generate_password_hash(password)
                )
                db.session.add(prof)
                db.session.commit()
                flash(f"Professeur {prenom} {nom} ajouté avec succès.", "success")

        # ── Supprimer un professeur ──
        elif action == 'delete':
            prof_id = request.form.get('prof_id')
            prof    = Professeur.query.filter_by(id=prof_id, ecole_id=ecole.id).first_or_404()
            db.session.delete(prof)
            db.session.commit()
            flash(f"Professeur {prof.nom_complet} supprimé.", "success")

        # ── Activer / Désactiver ──
        elif action == 'toggle':
            prof_id = request.form.get('prof_id')
            prof    = Professeur.query.filter_by(id=prof_id, ecole_id=ecole.id).first_or_404()
            prof.actif = not prof.actif
            db.session.commit()
            etat = "activé" if prof.actif else "désactivé"
            flash(f"Professeur {prof.nom_complet} {etat}.", "success")

        # ── Réinitialiser le mot de passe ──
        elif action == 'reset_password':
            prof_id      = request.form.get('prof_id')
            new_password = request.form.get('new_password', '').strip()
            prof         = Professeur.query.filter_by(id=prof_id, ecole_id=ecole.id).first_or_404()
            if len(new_password) < 6:
                flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "error")
            else:
                prof.mot_de_passe = generate_password_hash(new_password)
                db.session.commit()
                flash(f"Mot de passe de {prof.nom_complet} réinitialisé.", "success")

        return redirect(url_for('professeurs.gerer_professeurs'))

    return render_template('gerer_professeurs.html',
        ecole=ecole, profs=profs, classes=classes)


# ── Affectations (classes & matières) ──────────────────────────

@professeurs_bp.route('/professeurs/<int:prof_id>/affectations', methods=['GET', 'POST'])
@login_required
def gerer_affectations(prof_id):
    ecole = Ecole.query.get(session['ecole_id'])
    prof  = Professeur.query.filter_by(id=prof_id, ecole_id=ecole.id).first_or_404()
    classes = Classe.query.filter_by(ecole_id=ecole.id).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            classe_id  = request.form.get('classe_id', type=int)
            matiere_id = request.form.get('matiere_id', type=int)
            if not classe_id or not matiere_id:
                flash("Sélectionnez une classe et une matière.", "error")
            else:
                existing = ProfesseurAffectation.query.filter_by(
                    professeur_id=prof.id,
                    classe_id=classe_id,
                    matiere_id=matiere_id
                ).first()
                if existing:
                    flash("Cette affectation existe déjà.", "warning")
                else:
                    aff = ProfesseurAffectation(
                        professeur_id=prof.id,
                        classe_id=classe_id,
                        matiere_id=matiere_id
                    )
                    db.session.add(aff)
                    db.session.commit()
                    flash("Affectation ajoutée.", "success")

        elif action == 'remove':
            aff_id = request.form.get('aff_id', type=int)
            aff    = ProfesseurAffectation.query.get_or_404(aff_id)
            if aff.professeur_id == prof.id:
                db.session.delete(aff)
                db.session.commit()
                flash("Affectation supprimée.", "success")

        return redirect(url_for('professeurs.gerer_affectations', prof_id=prof.id))

    # Matières par classe pour le sélecteur AJAX
    matieres_par_classe = {}
    for c in classes:
        matieres_par_classe[c.id] = [
            {'id': m.id, 'nom': m.nom}
            for m in Matiere.query.filter_by(classe_id=c.id).all()
        ]

    return render_template('affectations_prof.html',
        ecole=ecole, prof=prof, classes=classes,
        affectations=prof.affectations,
        matieres_par_classe=matieres_par_classe)


# ════════════════════════════════════════════════════════════════
#  AUTHENTIFICATION PROFESSEUR
# ════════════════════════════════════════════════════════════════

@professeurs_bp.route('/prof/connexion', methods=['GET', 'POST'])
def prof_login():
    """Page de connexion pour les professeurs"""
    if 'professeur_id' in session:
        return redirect(url_for('professeurs.prof_dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        prof = Professeur.query.filter_by(email=email).first()

        if not prof or not check_password_hash(prof.mot_de_passe, password):
            flash("Email ou mot de passe incorrect.", "error")
            return redirect(url_for('professeurs.prof_login'))

        if not prof.actif:
            flash("Votre compte est désactivé. Contactez votre école.", "error")
            return redirect(url_for('professeurs.prof_login'))

        session['professeur_id'] = prof.id
        session['professeur_nom'] = prof.nom_complet
        session['user_type']     = 'professeur'
        flash(f"Bienvenue, {prof.prenom} !", "success")
        return redirect(url_for('professeurs.prof_dashboard'))

    return render_template('prof_login.html')


@professeurs_bp.route('/prof/deconnexion')
def prof_logout():
    session.pop('professeur_id', None)
    session.pop('professeur_nom', None)
    if session.get('user_type') == 'professeur':
        session.pop('user_type', None)
    return redirect(url_for('professeurs.prof_login'))


# ════════════════════════════════════════════════════════════════
#  ESPACE PROFESSEUR — Dashboard + Saisie notes
# ════════════════════════════════════════════════════════════════

@professeurs_bp.route('/prof/tableau-de-bord')
@prof_login_required
def prof_dashboard():
    """Dashboard du professeur — ses classes & matières affectées"""
    prof  = Professeur.query.get_or_404(session['professeur_id'])
    ecole = prof.ecole

    # Grouper les affectations par classe
    classes_matieres = {}
    for aff in prof.affectations:
        if aff.classe_id not in classes_matieres:
            classes_matieres[aff.classe_id] = {
                'classe':   aff.classe,
                'matieres': []
            }
        classes_matieres[aff.classe_id]['matieres'].append(aff.matiere)

    return render_template('prof_dashboard.html',
        prof=prof, ecole=ecole,
        classes_matieres=classes_matieres.values())


@professeurs_bp.route('/prof/notes/<int:classe_id>/<int:matiere_id>', methods=['GET', 'POST'])
@prof_login_required
def prof_saisir_notes(classe_id, matiere_id):
    """Saisie des notes par le professeur pour sa matière"""
    prof = Professeur.query.get_or_404(session['professeur_id'])

    # Vérifier que le prof est bien affecté à cette classe/matière
    aff = ProfesseurAffectation.query.filter_by(
        professeur_id=prof.id,
        classe_id=classe_id,
        matiere_id=matiere_id
    ).first()
    if not aff:
        flash("Vous n'êtes pas autorisé à saisir des notes pour cette matière.", "error")
        return redirect(url_for('professeurs.prof_dashboard'))

    classe  = aff.classe
    matiere = aff.matiere
    eleves  = Eleve.query.filter_by(classe_id=classe_id, archive=False).order_by(Eleve.nom, Eleve.prenom).all()
    trimestre = request.args.get('trimestre', 'T1')

    if request.method == 'POST':
        trimestre = request.form.get('trimestre', 'T1')
        for eleve in eleves:
            val_str = request.form.get(f'note_{eleve.id}', '').strip()
            if val_str == '':
                continue
            try:
                val = float(val_str.replace(',', '.'))
                val = max(0.0, min(20.0, val))
            except ValueError:
                continue

            note = Note.query.filter_by(
                eleve_id=eleve.id,
                matiere_id=matiere.id,
                trimestre=trimestre
            ).first()

            if note:
                note.note = val
            else:
                note = Note(
                    eleve_id=eleve.id,
                    matiere_id=matiere.id,
                    trimestre=trimestre,
                    note=val,
                    professeur_id=prof.id
                )
                db.session.add(note)

        db.session.commit()
        flash(f"Notes {trimestre} — {matiere.nom} enregistrées.", "success")
        return redirect(url_for('professeurs.prof_saisir_notes',
                                classe_id=classe_id, matiere_id=matiere_id,
                                trimestre=trimestre))

    # Charger les notes existantes
    notes_existantes = {
        n.eleve_id: n.note
        for n in Note.query.filter_by(
            matiere_id=matiere.id,
            trimestre=trimestre
        ).filter(Note.eleve_id.in_([e.id for e in eleves])).all()
    }

    return render_template('prof_saisir_notes.html',
        prof=prof, classe=classe, matiere=matiere,
        eleves=eleves, trimestre=trimestre,
        notes_existantes=notes_existantes)


# ── API AJAX — matières par classe ───────────────────────#──────
@professeurs_bp.route('/api/matieres/<int:classe_id>')
@login_required
def api_matieres_classe(classe_id):
    from flask import jsonify
    matieres = Matiere.query.filter_by(classe_id=classe_id).all()
    return jsonify([{'id': m.id, 'nom': m.nom} for m in matieres])

