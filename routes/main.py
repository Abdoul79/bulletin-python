
from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import db, Ecole, Classe, Eleve, Matiere
from utils import login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request
from models import db, Ecole

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal de l'école"""
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole:
        flash("École introuvable.", "error")
        return redirect(url_for('auth.login'))
    
    classes = Classe.query.filter_by(ecole_id=ecole.id).all()
    
    # Enrichir les classes avec des statistiques
    for classe in classes:
        classe.nb_eleves = Eleve.query.filter_by(classe_id=classe.id, archive=False).count()
        classe.nb_matieres = Matiere.query.filter_by(classe_id=classe.id).count()
    
    return render_template('ecole_dashboard.html', ecole=ecole, classes=classes)


@main_bp.route('/ecole/classe/<int:classe_id>')
@login_required
def voir_classe(classe_id):
    """Vue d'ensemble d'une classe"""
    classe = Classe.query.get_or_404(classe_id)
    
    # Vérifier que la classe appartient à l'école connectée
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))
    
    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    matieres = Matiere.query.filter_by(classe_id=classe_id).all()

    return render_template(
        'voir_classe.html',
        classe=classe,
        eleves=eleves,
        matieres=matieres,
        nb_eleves=len(eleves),
        nb_matieres=len(matieres)
    )


@main_bp.route('/ecole/gestion/<int:classe_id>')
@login_required
def gestion_classe(classe_id):
    """Page de gestion complète d'une classe"""
    classe = Classe.query.get_or_404(classe_id)
    
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))
    
    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    matieres = Matiere.query.filter_by(classe_id=classe_id).all()

    return render_template(
        'voir_classe.html',  # Utilise le template existant
        classe=classe,
        eleves=eleves,
        matieres=matieres,
        nb_eleves=len(eleves),
        nb_matieres=len(matieres)
    )

@main_bp.route('/changer_mot_de_passe', methods=['GET', 'POST'])
def changer_mot_de_passe():
    """Permettre à l'école de changer son mot de passe"""
    if 'ecole_id' not in session:
        flash("Vous devez être connecté pour accéder à cette page.", "error")
        return redirect(url_for('auth.login'))
    
    ecole = Ecole.query.get(session['ecole_id'])
    
    if request.method == 'POST':
        ancien_mdp = request.form.get('ancien_mdp')
        nouveau_mdp = request.form.get('nouveau_mdp')
        confirmer_mdp = request.form.get('confirmer_mdp')
        
        # Validation
        if not all([ancien_mdp, nouveau_mdp, confirmer_mdp]):
            flash("Tous les champs sont obligatoires", "error")
            return render_template('changer_mot_de_passe.html', ecole=ecole)
        
        # Vérifier l'ancien mot de passe
        if not check_password_hash(ecole.mot_de_passe, ancien_mdp):
            flash("L'ancien mot de passe est incorrect", "error")
            return render_template('changer_mot_de_passe.html', ecole=ecole)
        
        # Vérifier que les nouveaux mots de passe correspondent
        if nouveau_mdp != confirmer_mdp:
            flash("Les nouveaux mots de passe ne correspondent pas", "error")
            return render_template('changer_mot_de_passe.html', ecole=ecole)
        
        # Vérifier la longueur du mot de passe
        if len(nouveau_mdp) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères", "error")
            return render_template('changer_mot_de_passe.html', ecole=ecole)
        
        try:
            # Mettre à jour le mot de passe
            ecole.mot_de_passe = generate_password_hash(nouveau_mdp)
            db.session.commit()
            flash("Mot de passe changé avec succès !", "success")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors du changement de mot de passe", "error")
            return render_template('changer_mot_de_passe.html', ecole=ecole)
    
    return render_template('changer_mot_de_passe.html', ecole=ecole)

@main_bp.route('/changer_mot_de_passe_ar', methods=['GET', 'POST'])
@login_required
def changer_mot_de_passe_ar():
    if 'ecole_id' not in session:
        return redirect(url_for('auth.login'))

    ecole = Ecole.query.get(session['ecole_id'])

    if request.method == 'POST':
        ancien_mdp    = request.form.get('ancien_mdp')
        nouveau_mdp   = request.form.get('nouveau_mdp')
        confirmer_mdp = request.form.get('confirmer_mdp')

        if not all([ancien_mdp, nouveau_mdp, confirmer_mdp]):
            flash("جميع الحقول إلزامية", "error")
            return render_template('changer_mot_de_passe_ar.html', ecole=ecole)
        if not check_password_hash(ecole.mot_de_passe, ancien_mdp):
            flash("كلمة المرور الحالية غير صحيحة", "error")
            return render_template('changer_mot_de_passe_ar.html', ecole=ecole)
        if nouveau_mdp != confirmer_mdp:
            flash("كلمتا المرور غير متطابقتين", "error")
            return render_template('changer_mot_de_passe_ar.html', ecole=ecole)
        if len(nouveau_mdp) < 6:
            flash("كلمة المرور يجب أن تحتوي على 6 أحرف على الأقل", "error")
            return render_template('changer_mot_de_passe_ar.html', ecole=ecole)

        try:
            ecole.mot_de_passe = generate_password_hash(nouveau_mdp)
            db.session.commit()
            flash("تم تغيير كلمة المرور بنجاح!", "success")
            return redirect(url_for('main.dashboard_ar'))  # ✅ toujours dashboard_ar
        except:
            db.session.rollback()
            flash("خطأ أثناء تغيير كلمة المرور", "error")
            return render_template('changer_mot_de_passe_ar.html', ecole=ecole)

    return render_template('changer_mot_de_passe_ar.html', ecole=ecole)


@main_bp.route('/dashboard_ar')
def dashboard_ar():
    """Dashboard en arabe pour les écoles franco-arabes"""
    if 'ecole_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "error")
        return redirect(url_for('auth.login'))
    
    # Vérifier que c'est bien une école franco-arabe
    ecole = Ecole.query.get(session['ecole_id'])
    if ecole.type_ecole != 'franco-arabe':
        return redirect(url_for('main.dashboard'))
    
    classes = Classe.query.filter_by(ecole_id=session['ecole_id']).all()
    
    # Calculer les statistiques
    total_classes = len(classes)
    total_eleves = sum(len(classe.eleves) for classe in classes)
    
    return render_template('dashboard_ar.html', 
                         ecole=ecole,
                         classes=classes,
                         total_classes=total_classes,
                         total_eleves=total_eleves)

@main_bp.route('/ecole/classe_ar/<int:classe_id>')
@login_required
def voir_classe_ar(classe_id):
    ecole = Ecole.query.get(session['ecole_id'])
    if ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé à cette classe.", "error")
        return redirect(url_for('main.dashboard_ar'))

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    matieres = Matiere.query.filter_by(classe_id=classe_id).all()

    return render_template(
        'voir_classe_ar.html',
        ecole=ecole,          # ✅ Ajouté ici#
        classe=classe,
        eleves=eleves,
        matieres=matieres,
        nb_eleves=len(eleves),
        nb_matieres=len(matieres)
    )


@main_bp.route('/ecole/gestion_ar/<int:classe_id>')
@login_required
def gestion_classe_ar(classe_id):
    ecole = Ecole.query.get(session['ecole_id'])
    if ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé à cette classe.", "error")
        return redirect(url_for('main.dashboard_ar'))

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False).all()
    matieres = Matiere.query.filter_by(classe_id=classe_id).all()

    return render_template(
        'voir_classe_ar.html',
        ecole=ecole,          # ✅ Ajouté ici
        classe=classe,
        eleves=eleves,
        matieres=matieres,
        nb_eleves=len(eleves),
        nb_matieres=len(matieres)
    )


