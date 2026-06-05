from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Ecole, Classe
from utils import format_filename
from datetime import datetime

# ── IMPORTS À AJOUTER EN HAUT DE routes/auth.py ──────────────
import secrets
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


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
            session['last_activity'] = datetime.utcnow().isoformat()
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

    # Écoles actives/suspendues (pas les demandes en attente)
    ecoles = Ecole.query.filter(Ecole.statut != 'en_attente').order_by(Ecole.id.desc()).all()
    # Demandes d'inscription en attente de validation
    demandes = Ecole.query.filter_by(statut='en_attente').order_by(Ecole.id.desc()).all()

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
            return render_template('register_ecole.html', ecoles=ecoles, demandes=demandes)

        if Ecole.query.filter_by(email=email).first():
            flash("❌ Cet email est déjà utilisé par une autre école.", "error")
            return render_template('register_ecole.html', ecoles=ecoles, demandes=demandes)

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
                type_ecole=type_ecole,
                statut='actif'          # Ajout admin → directement actif
            )
            db.session.add(ecole)
            db.session.commit()

            flash(f"✅ École '{nom}' enregistrée avec succès !", "success")
            return redirect(url_for('auth.register_ecole'))

        except Exception as e:
            db.session.rollback()
            flash("❌ Erreur lors de l'enregistrement de l'école.", "error")
            return render_template('register_ecole.html', ecoles=ecoles, demandes=demandes)

    return render_template('register_ecole.html', ecoles=ecoles, demandes=demandes)


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
    type_ecole = request.form.get('type_ecole', 'francaise')

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
            ecole.type_ecole = type_ecole
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
            ecole.statut = 'suspendu' if action == 'suspendre' else 'actif'
            db.session.commit()
            action_text = 'suspendue' if ecole.statut == 'suspendu' else 'activée'
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


@auth_bp.route('/admin/approve_ecole', methods=['POST'])
def admin_approve_ecole():
    """Accepter une demande d'inscription d'école"""
    if not is_admin_logged_in():
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for('auth.admin_login'))

    ecole_id = request.form.get('ecole_id')

    try:
        ecole = Ecole.query.get(ecole_id)
        if ecole and ecole.statut == 'en_attente':
            ecole.statut = 'actif'
            db.session.commit()
            flash(f"✅ Demande de '{ecole.nom}' acceptée. L'école est maintenant active.", "success")
        else:
            flash("Demande introuvable ou déjà traitée.", "error")
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de l'approbation.", "error")
        print(f"Erreur: {e}")

    return redirect(url_for('auth.register_ecole', tab='demandes'))


@auth_bp.route('/admin/reject_ecole', methods=['POST'])
def admin_reject_ecole():
    """Refuser et supprimer une demande d'inscription d'école"""
    if not is_admin_logged_in():
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for('auth.admin_login'))

    ecole_id = request.form.get('ecole_id')

    try:
        ecole = Ecole.query.get(ecole_id)
        if ecole and ecole.statut == 'en_attente':
            nom = ecole.nom
            # Supprimer le logo si présent
            if ecole.logo:
                try:
                    logo_path = os.path.join('static/img', ecole.logo)
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                except Exception as e:
                    print(f"Erreur suppression logo: {e}")
            db.session.delete(ecole)
            db.session.commit()
            flash(f"❌ Demande de '{nom}' refusée et supprimée.", "warning")
        else:
            flash("Demande introuvable ou déjà traitée.", "error")
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors du refus.", "error")
        print(f"Erreur: {e}")

    return redirect(url_for('auth.register_ecole', tab='demandes'))


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

            if statut == 'en_attente':
                flash("⏳ Votre demande d'inscription est en attente de validation par l'administrateur.", "error")
                return render_template('login.html')

            if statut == 'suspendu':
                flash("Votre école est actuellement suspendue. Contactez l'administrateur.", "error")
                return render_template('login.html')

            session.clear()
            session['ecole_id'] = ecole.id
            session['ecole_nom'] = ecole.nom
            session['user_type'] = 'ecole'
            session['type_ecole'] = ecole.type_ecole
            session['last_activity'] = datetime.utcnow().isoformat()

            flash(f"Bienvenue {ecole.nom} !", "success")

            if ecole.type_ecole == 'franco-arabe':
                return redirect(url_for('main.dashboard_ar'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash("Email ou mot de passe incorrect", "error")

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def ecole_register():
    """Auto-inscription d'une école — compte créé avec statut 'en_attente'"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        directeur = request.form.get('directeur', '').strip()
        adresse = request.form.get('adresse', '').strip()
        telephone = request.form.get('telephone', '').strip()
        type_ecole = request.form.get('type_ecole', 'francaise')

        if not all([nom, email, password]):
            flash("Nom, email et mot de passe sont obligatoires.", "error")
            return render_template('login.html', open_register=True)

        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            return render_template('login.html', open_register=True)

        if Ecole.query.filter_by(email=email).first():
            flash("❌ Cet email est déjà utilisé.", "error")
            return render_template('login.html', open_register=True)

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
                type_ecole=type_ecole,
                statut='en_attente'     # ← En attente de validation admin
            )
            db.session.add(ecole)
            db.session.commit()

            # Redirige vers login avec indicateur de succès
            return redirect(url_for('auth.login', registered=1))

        except Exception as e:
            db.session.rollback()
            flash("❌ Erreur lors de l'inscription. Veuillez réessayer.", "error")
            print(f"Erreur inscription: {e}")
            return render_template('login.html', open_register=True)

    # GET → affiche le formulaire d'inscription
    return render_template('login.html', open_register=True)


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



"""
Ajouter dans routes/auth.py
Système mot de passe oublié avec SendGrid
"""

# ── IMPORTS À AJOUTER EN HAUT DE routes/auth.py ──────────────

# ── AJOUTER DANS models.py : table PasswordResetToken ────────


# ════════════════════════════════════════════════════════════════
#  HELPER — Envoi email SendGrid
# ════════════════════════════════════════════════════════════════

def envoyer_email_reset(destinataire_email, destinataire_nom, reset_url):
    """Envoie l'email de réinitialisation via SendGrid"""
    api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@edubulletin.app')

    if not api_key:
        print("⚠️ SENDGRID_API_KEY non configuré")
        return False

    message = Mail(
        from_email=from_email,
        to_emails=destinataire_email,
        subject='🔐 Réinitialisation de votre mot de passe EduBulletin',
        html_content=f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:'DM Sans',Arial,sans-serif;background:#f5f0e8;margin:0;padding:24px;">
  <div style="max-width:520px;margin:0 auto;background:white;border-radius:18px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background:#0d1117;padding:24px 32px;text-align:center;">
      <div style="display:inline-flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;background:#c9a84c;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;">🎓</div>
        <span style="font-size:1.1rem;font-weight:800;color:#e8edf2;">EduBulletin</span>
      </div>
    </div>

    <!-- Body -->
    <div style="padding:32px;">
      <h2 style="font-size:1.2rem;color:#0d1117;margin-bottom:8px;">Réinitialisation du mot de passe</h2>
      <p style="color:#6b7685;font-size:13px;line-height:1.7;margin-bottom:24px;">
        Bonjour <strong style="color:#0d1117;">{destinataire_nom}</strong>,<br>
        Vous avez demandé à réinitialiser votre mot de passe EduBulletin.
        Cliquez sur le bouton ci-dessous pour en créer un nouveau.
      </p>

      <!-- Bouton -->
      <div style="text-align:center;margin-bottom:24px;">
        <a href="{reset_url}"
           style="display:inline-block;background:#0d1117;color:#c9a84c;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:800;font-size:14px;letter-spacing:0.3px;">
          🔐 Réinitialiser mon mot de passe
        </a>
      </div>

      <!-- Lien texte -->
      <p style="color:#6b7685;font-size:11px;text-align:center;margin-bottom:16px;">
        Ou copiez ce lien dans votre navigateur :<br>
        <a href="{reset_url}" style="color:#c9a84c;word-break:break-all;">{reset_url}</a>
      </p>

      <!-- Avertissement -->
      <div style="background:#fff8e7;border:1px solid rgba(201,168,76,0.3);border-radius:10px;padding:12px 16px;">
        <p style="color:#7a5c10;font-size:11px;margin:0;line-height:1.6;">
          ⏰ <strong>Ce lien expire dans 1 heure.</strong><br>
          Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
          Votre mot de passe ne sera pas modifié.
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="background:#f8f9fa;border-top:1px solid #e8edf2;padding:16px 32px;text-align:center;">
      <p style="color:#aab0ba;font-size:10px;margin:0;">
        EduBulletin — Système de gestion scolaire 🇨🇮<br>
        Cet email a été envoyé à {destinataire_email}
      </p>
    </div>

  </div>
</body>
</html>
        """
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✅ Email reset envoyé à {destinataire_email} — status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Erreur SendGrid : {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  ROUTE 1 — Formulaire "mot de passe oublié"
# ════════════════════════════════════════════════════════════════

@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    if request.method == 'POST':
        from models import Ecole, PasswordResetToken

        email = request.form.get('email', '').strip().lower()
        if not email:
            flash("Veuillez saisir votre adresse email.", "error")
            return redirect(url_for('auth.mot_de_passe_oublie'))

        ecole = Ecole.query.filter_by(email=email).first()

        # Toujours afficher le même message (sécurité — ne pas révéler si l'email existe)
        if ecole:
            # Invalider les anciens tokens
            from models import PasswordResetToken
            PasswordResetToken.query.filter_by(ecole_id=ecole.id, used=False).update({'used': True})
            db.session.flush()

            # Créer un nouveau token
            token = secrets.token_urlsafe(32)
            reset_token = PasswordResetToken(
                ecole_id=ecole.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset_token)
            db.session.commit()

            # Construire l'URL de reset
            base_url = os.environ.get('APP_BASE_URL', request.host_url.rstrip('/'))
            reset_url = f"{base_url}/reinitialiser-mot-de-passe/{token}"

            # Envoyer l'email
            envoyer_email_reset(ecole.email, ecole.nom, reset_url)

        flash(
            "Si cette adresse email est enregistrée, vous recevrez un lien de réinitialisation dans quelques minutes.",
            "success"
        )
        return redirect(url_for('auth.mot_de_passe_oublie'))

    return render_template('forgot_password.html')


# ════════════════════════════════════════════════════════════════
#  ROUTE 2 — Formulaire de nouveau mot de passe
# ════════════════════════════════════════════════════════════════

@auth_bp.route('/reinitialiser-mot-de-passe/<string:token>', methods=['GET', 'POST'])
def reinitialiser_mot_de_passe(token):
    from models import PasswordResetToken
    from werkzeug.security import generate_password_hash

    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()

    # Vérifier validité du token
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        flash("Ce lien est invalide ou a expiré. Veuillez faire une nouvelle demande.", "error")
        return redirect(url_for('auth.mot_de_passe_oublie'))

    if request.method == 'POST':
        password         = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            return redirect(url_for('auth.reinitialiser_mot_de_passe', token=token))

        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.reinitialiser_mot_de_passe', token=token))

        # Mettre à jour le mot de passe
        ecole = reset_token.ecole
        ecole.mot_de_passe = generate_password_hash(password)

        # Invalider le token
        reset_token.used = True
        db.session.commit()

        flash("Mot de passe mis à jour avec succès ! Vous pouvez vous connecter.", "success")
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)