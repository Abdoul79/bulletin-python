"""
Ajouter ces routes dans routes/auth.py (inscription école)
ET dans routes/admin.py (activation admin)
"""

# ════════════════════════════════════════════════════════
#  1. Dans routes/auth.py — Route inscription libre école
# ════════════════════════════════════════════════════════

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Ecole
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__)

ADMIN_KEY = os.environ.get('ADMIN_REGISTER_KEY', 'edubulletin-admin-2024')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register_ecole():
    if request.method == 'POST':
        mode     = request.form.get('mode', 'ecole')   # 'ecole' ou 'admin'
        nom      = request.form.get('nom', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        type_ecole = request.form.get('type_ecole', '')
        ville    = request.form.get('ville', '').strip()
        adresse  = request.form.get('adresse', '').strip()
        telephone = request.form.get('telephone', '').strip()
        directeur = request.form.get('directeur', '').strip()
        annee_scolaire = request.form.get('annee_scolaire', '2024-2025').strip()

        # ── Validations ────────────────────────────────────
        if not nom or not email or not password or not type_ecole:
            flash('Veuillez remplir tous les champs obligatoires.', 'error')
            return redirect(url_for('auth.register_ecole'))

        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return redirect(url_for('auth.register_ecole'))

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
            return redirect(url_for('auth.register_ecole'))

        if type_ecole not in ('francaise', 'arabe', 'franco_arabe'):
            flash('Type d\'école invalide.', 'error')
            return redirect(url_for('auth.register_ecole'))

        if Ecole.query.filter_by(email=email).first():
            flash('Cette adresse email est déjà utilisée.', 'error')
            return redirect(url_for('auth.register_ecole'))

        # ── Mode admin : vérifier la clé ───────────────────
        is_active = False
        if mode == 'admin':
            admin_key = request.form.get('admin_key', '')
            if admin_key != ADMIN_KEY:
                flash('Clé d\'administration incorrecte.', 'error')
                return redirect(url_for('auth.register_ecole'))
            is_active = True

        # ── Créer l'école ──────────────────────────────────
        ecole = Ecole(
            nom=nom,
            email=email,
            password=generate_password_hash(password),
            type_ecole=type_ecole,
            ville=ville or None,
            adresse=adresse or None,
            telephone=telephone or None,
            directeur=directeur or None,
            annee_scolaire=annee_scolaire,
            is_active=is_active,                 # False = en attente
            date_inscription=datetime.utcnow(),
        )
        db.session.add(ecole)
        db.session.commit()

        if is_active:
            flash(f'École "{nom}" créée et activée avec succès !', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Affiche l'écran de succès "en attente"
            flash('pending', 'info')
            return redirect(url_for('auth.register_ecole'))

    return render_template('register_ecole.html')


# ════════════════════════════════════════════════════════
#  2. Dans routes/admin.py — Routes activation admin
# ════════════════════════════════════════════════════════

# admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/ecoles/activation')
def gestion_activation():
    """Page admin pour activer/désactiver les écoles"""
    ecoles_pending = Ecole.query.filter_by(is_active=False).order_by(Ecole.date_inscription.desc()).all()
    ecoles_actives  = Ecole.query.filter_by(is_active=True).order_by(Ecole.nom).all()
    return render_template('admin_activation.html',
        ecoles_pending=ecoles_pending,
        ecoles_actives=ecoles_actives
    )


@admin_bp.route('/ecoles/<int:ecole_id>/activer', methods=['POST'])
def activer_ecole(ecole_id):
    ecole = Ecole.query.get_or_404(ecole_id)
    ecole.is_active = True
    db.session.commit()
    flash(f'École "{ecole.nom}" activée avec succès.', 'success')
    return redirect(url_for('admin.gestion_activation'))


@admin_bp.route('/ecoles/<int:ecole_id>/desactiver', methods=['POST'])
def desactiver_ecole(ecole_id):
    ecole = Ecole.query.get_or_404(ecole_id)
    ecole.is_active = False
    db.session.commit()
    flash(f'École "{ecole.nom}" désactivée.', 'info')
    return redirect(url_for('admin.gestion_activation'))


@admin_bp.route('/ecoles/<int:ecole_id>/rejeter', methods=['POST'])
def rejeter_ecole(ecole_id):
    ecole = Ecole.query.get_or_404(ecole_id)
    nom = ecole.nom
    db.session.delete(ecole)
    db.session.commit()
    flash(f'Demande de "{nom}" rejetée et supprimée.', 'info')
    return redirect(url_for('admin.gestion_activation'))


# ════════════════════════════════════════════════════════
#  3. Dans routes/auth.py — Bloquer login si pas actif
# ════════════════════════════════════════════════════════

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        ecole = Ecole.query.filter_by(email=email).first()

        if not ecole or not check_password_hash(ecole.password, password):
            flash('Email ou mot de passe incorrect.', 'error')
            return redirect(url_for('auth.login'))

        # ── Vérifier si le compte est activé ──────────────
        if not ecole.is_active:
            flash(
                'Votre compte est en attente d\'activation par un administrateur. '
                'Vous serez notifié par email dès que votre compte sera activé.',
                'warning'
            )
            return redirect(url_for('auth.login'))

        session['ecole_id'] = ecole.id
        # Redirection selon type
        if ecole.type_ecole in ('arabe', 'franco_arabe'):
            return redirect(url_for('main.dashboard_ar'))
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')


# ════════════════════════════════════════════════════════
#  4. Modèle Ecole — Ajouter les nouveaux champs
# ════════════════════════════════════════════════════════

"""
Dans models.py, ajouter dans la classe Ecole :

class Ecole(db.Model):
    # ... champs existants ...
    is_active        = db.Column(db.Boolean, default=False, nullable=False)  # ← NOUVEAU
    date_inscription = db.Column(db.DateTime, nullable=True)                 # ← NOUVEAU
    adresse          = db.Column(db.String(200), nullable=True)              # ← si pas déjà
    telephone        = db.Column(db.String(30), nullable=True)               # ← si pas déjà
"""


# ════════════════════════════════════════════════════════
#  5. Migration base de données
# ════════════════════════════════════════════════════════

"""
flask db migrate -m "add is_active date_inscription to ecole"
flask db upgrade

# Activer les écoles existantes (ne pas les bloquer)
flask shell
>>> from models import db, Ecole
>>> Ecole.query.update({'is_active': True})
>>> db.session.commit()
>>> exit()
"""


# ════════════════════════════════════════════════════════
#  6. Variable d'environnement Railway
# ════════════════════════════════════════════════════════

"""
Dans Railway → Variables :
ADMIN_REGISTER_KEY = votre_cle_secrete_ici

En local dans .env :
ADMIN_REGISTER_KEY=votre_cle_secrete_ici
"""