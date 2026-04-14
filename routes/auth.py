from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Ecole, Classe
from utils import format_filename
from datetime import datetime

import os

auth_bp = Blueprint('auth', __name__)


# ======================================
# CONFIGURATION ADMINISTRATEUR
# ======================================
ADMIN_CREDENTIALS = {
    'email': 'abdoul7913@gmail.com',
    'password': 'Maman5516',
}

def is_admin_logged_in():
    """Vérifier si un administrateur est connecté"""
    return session.get('user_type') == 'admin' and session.get('admin_logged_in') == True

def is_ecole_logged_in():
    """Vérifier si une école est connectée"""
    return session.get('user_type') == 'ecole' and 'ecole_id' in session


# ======================================
# ROUTES PUBLIQUES
# ======================================

@auth_bp.route('/')
def index():
    """Page d'accueil avec bouton WhatsApp si numéro configuré"""
    from models import Config
    whatsapp_number = Config.get('whatsapp_number', '')
    whatsapp_clean = ''.join(filter(str.isdigit, whatsapp_number))
    return render_template('index.html', whatsapp_number=whatsapp_clean)


# ======================================
# ROUTES ADMINISTRATEUR
# ======================================

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Connexion administrateur"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email et mot de passe administrateur requis.", "error")
            return render_template('admin_login.html')

        if email == ADMIN_CREDENTIALS['email'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            session['user_type'] = 'admin'
            session['admin_email'] = email
            session['last_activity'] = datetime.utcnow().isoformat()  # ← démarre le timer
            flash("✅ Connexion administrateur réussie !", "success")
            return redirect(url_for('auth.register_ecole'))
        else:
            flash("❌ Identifiants administrateur incorrects", "error")

    return render_template('admin_login.html')


@auth_bp.route('/admin/register', methods=['GET', 'POST'])
def register_ecole():
    """Enregistrement et gestion des écoles - RÉSERVÉ AUX ADMINISTRATEURS"""

    if not is_admin_logged_in():
        flash("⚠️ Accès réservé aux administrateurs.", "warning")
        return redirect(url_for('auth.admin_login'))

    ecoles = Ecole.query.order_by(Ecole.id.desc()).all()

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        directeur = request.form.get('directeur', '').strip()
        adresse = request.form.get('adresse', '').strip()
        telephone = request.form.get('telephone', '').strip()
        type_ecole = request.form.get('type_ecole', 'francaise')

        if not all([nom, email, password]):
            flash("Tous les champs obligatoires doivent être remplis.", "error")
            return render_template('register_ecole.html', ecoles=ecoles)

        if Ecole.query.filter_by(email=email).first():
            flash("❌ Cet email est déjà utilisé par une autre école.", "error")
            return render_template('register_ecole.html', ecoles=ecoles)

        logo = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file.filename != '':
                filename = format_filename(file.filename, f"logo_{email.replace('@', '_').replace('.', '_')}")
                upload_dir = 'static/img'
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                logo = filename

        try:
            ecole = Ecole(
                nom=nom,
                email=email,
                mot_de_passe=generate_password_hash(password),
                directeur=directeur,
                adresse=adresse,
                telephone=telephone,
                logo=logo,
                type_ecole=type_ecole
            )
            db.session.add(ecole)
            db.session.commit()

            flash(f"✅ École '{nom}' enregistrée avec succès !", "success")
            return redirect(url_for('auth.register_ecole'))

        except Exception as e:
            db.session.rollback()
            flash("❌ Erreur lors de l'enregistrement de l'école.", "error")
            return render_template('register_ecole.html', ecoles=ecoles)

    return render_template('register_ecole.html', ecoles=ecoles)


@auth_bp.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """Paramètres admin : numéro WhatsApp, etc."""
    if not is_admin_logged_in():
        flash("⚠️ Accès réservé aux administrateurs.", "warning")
        return redirect(url_for('auth.admin_login'))

    from models import Config

    if request.method == 'POST':
        whatsapp = request.form.get('whatsapp_number', '').strip()
        Config.set('whatsapp_number', whatsapp)
        flash("✅ Paramètres enregistrés avec succès !", "success")
        return redirect(url_for('auth.admin_settings'))

    whatsapp_number = Config.get('whatsapp_number', '')
    return render_template('admin_settings.html', whatsapp_number=whatsapp_number)


@auth_bp.route('/admin/edit_ecole', methods=['POST'])
def admin_edit_ecole():
    """Modifier une école"""
    if not is_admin_logged_in():
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for('auth.admin_login'))

    ecole_id = request.form.get('ecole_id')
    nom = request.form.get('nom')
    email = request.form.get('email')
    directeur = request.form.get('directeur')
    telephone = request.form.get('telephone')
    adresse = request.form.get('adresse')

    try:
        ecole = Ecole.query.get(ecole_id)
        if ecole:
            autre_ecole = Ecole.query.filter(Ecole.email == email, Ecole.id != ecole_id).first()
            if autre_ecole:
                flash("Cet email est déjà utilisé par une autre école", "error")
                return redirect(url_for('auth.register_ecole'))

            ecole.nom = nom
            ecole.email = email
            ecole.directeur = directeur
            ecole.telephone = telephone
            ecole.adresse = adresse
            db.session.commit()
            flash(f"École '{nom}' modifiée avec succès", "success")
        else:
            flash("École introuvable", "error")
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de la modification", "error")
        print(f"Erreur: {e}")

    return redirect(url_for('auth.register_ecole'))


@auth_bp.route('/admin/toggle_status', methods=['POST'])
def admin_toggle_status():
    """Suspendre/Activer une école"""
    if not is_admin_logged_in():
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for('auth.admin_login'))

    ecole_id = request.form.get('ecole_id')
    action = request.form.get('action')

    try:
        ecole = Ecole.query.get(ecole_id)
        if ecole:
            nouveau_statut = 'suspendu' if action == 'suspendre' else 'actif'

            if hasattr(ecole, 'statut'):
                ecole.statut = nouveau_statut
            else:
                setattr(ecole, 'statut', nouveau_statut)

            db.session.commit()

            action_text = 'suspendue' if nouveau_statut == 'suspendu' else 'activée'
            flash(f"École '{ecole.nom}' {action_text} avec succès", "success")
        else:
            flash("École introuvable", "error")
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors du changement de statut", "error")
        print(f"Erreur: {e}")

    return redirect(url_for('auth.register_ecole'))


@auth_bp.route('/admin/delete_ecole', methods=['POST'])
def admin_delete_ecole():
    """Supprimer une école définitivement avec toutes ses données"""
    if not is_admin_logged_in():
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for('auth.admin_login'))

    ecole_id = request.form.get('ecole_id')

    try:
        ecole = Ecole.query.get(ecole_id)
        if ecole:
            nom = ecole.nom

            if hasattr(ecole, 'logo') and ecole.logo:
                try:
                    logo_path = os.path.join('static/img', ecole.logo)
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                except Exception as e:
                    print(f"Erreur suppression logo: {e}")

            from models import Eleve, Note, Matiere

            classes = Classe.query.filter_by(ecole_id=ecole_id).all()

            for classe in classes:
                eleves = Eleve.query.filter_by(classe_id=classe.id).all()

                for eleve in eleves:
                    Note.query.filter_by(eleve_id=eleve.id).delete()
                    db.session.delete(eleve)

                Matiere.query.filter_by(classe_id=classe.id).delete()
                db.session.delete(classe)

            db.session.delete(ecole)
            db.session.commit()

            flash(f"École '{nom}' et toutes ses données supprimées définitivement", "success")
        else:
            flash("École introuvable", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}", "error")
        print(f"Erreur détaillée: {e}")
        import traceback
        traceback.print_exc()

    return redirect(url_for('auth.register_ecole'))


@auth_bp.route('/admin/logout')
def admin_logout():
    """Déconnexion administrateur"""
    session.clear()
    flash("Déconnexion administrateur réussie", "info")
    return redirect(url_for('auth.index'))


# ======================================
# ROUTES ÉCOLES
# ======================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion d'une école"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email et mot de passe requis.", "error")
            return render_template('login.html')

        ecole = Ecole.query.filter_by(email=email).first()

        if ecole and check_password_hash(ecole.mot_de_passe, password):
            statut = getattr(ecole, 'statut', 'actif')
            if statut == 'suspendu':
                flash("Votre école est actuellement suspendue. Contactez l'administrateur.", "error")
                return render_template('login.html')

            session.clear()
            session['ecole_id'] = ecole.id
            session['ecole_nom'] = ecole.nom
            session['user_type'] = 'ecole'
            session['type_ecole'] = ecole.type_ecole
            session['last_activity'] = datetime.utcnow().isoformat()  # ← démarre le timer

            flash(f"Bienvenue {ecole.nom} !", "success")

            if ecole.type_ecole == 'franco-arabe':
                return redirect(url_for('main.dashboard_ar'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash("Email ou mot de passe incorrect", "error")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Déconnexion (école ou admin)"""
    user_type = session.get('user_type')
    session.clear()

    if user_type == 'admin':
        flash("Déconnexion administrateur réussie.", "info")
    else:
        flash("Vous avez été déconnecté.", "info")

    return redirect(url_for('auth.index'))
