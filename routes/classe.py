from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Classe, Eleve, Matiere, Ecole
from utils import login_required

classe_bp = Blueprint('classe', __name__, url_prefix='/ecole')


@classe_bp.route('/add_classe', methods=['GET', 'POST'])
@login_required
def add_classe():
    """Gestion des classes (ajout, modification, suppression)"""
    if request.method == 'POST':
        action = request.form.get('action')
        classe_id = request.form.get('classe_id')

        try:
            if action == 'add':
                nom = request.form.get('nom', '').strip()
                annee_scolaire = request.form.get('annee_scolaire', '2025-2026')
                
                if not nom:
                    flash("Le nom de la classe est obligatoire.", "error")
                    return redirect(url_for('classe.add_classe'))
                
                # Vérifier les doublons
                if Classe.query.filter_by(ecole_id=session['ecole_id'], nom=nom).first():
                    flash("Une classe avec ce nom existe déjà.", "warning")
                    return redirect(url_for('classe.add_classe'))
                
                classe = Classe(
                    nom=nom,
                    ecole_id=session['ecole_id'],
                    annee_scolaire=annee_scolaire
                )
                db.session.add(classe)
                db.session.commit()
                flash(f"Classe '{nom}' ajoutée avec succès !", "success")

            elif action == 'edit' and classe_id:
                classe = Classe.query.get_or_404(classe_id)
                
                # Vérifier l'appartenance à l'école
                if classe.ecole_id != session['ecole_id']:
                    flash("Action non autorisée.", "error")
                    return redirect(url_for('classe.add_classe'))
                
                nom = request.form.get('nom', '').strip()
                annee_scolaire = request.form.get('annee_scolaire', '2025-2026')
                
                if not nom:
                    flash("Le nom de la classe est obligatoire.", "error")
                    return redirect(url_for('classe.add_classe'))
                
                # Vérifier les doublons (sauf pour cette classe)
                existing = Classe.query.filter(
                    Classe.ecole_id == session['ecole_id'],
                    Classe.nom == nom,
                    Classe.id != classe.id
                ).first()
                
                if existing:
                    flash("Une classe avec ce nom existe déjà.", "warning")
                    return redirect(url_for('classe.add_classe'))
                
                classe.nom = nom
                classe.annee_scolaire = annee_scolaire
                db.session.commit()
                flash(f"Classe '{nom}' modifiée.", "success")

            elif action == 'delete' and classe_id:
                classe = Classe.query.get_or_404(classe_id)
                
                # Vérifier l'appartenance à l'école
                if classe.ecole_id != session['ecole_id']:
                    flash("Action non autorisée.", "error")
                    return redirect(url_for('classe.add_classe'))
                
                nom = classe.nom
                
                # Compter les éléments liés
                nb_eleves = Eleve.query.filter_by(classe_id=classe.id).count()
                nb_matieres = Matiere.query.filter_by(classe_id=classe.id).count()
                
                if nb_eleves > 0 or nb_matieres > 0:
                    flash(f"Impossible de supprimer la classe '{nom}'. Elle contient {nb_eleves} élève(s) et {nb_matieres} matière(s).", "warning")
                    return redirect(url_for('classe.add_classe'))
                
                db.session.delete(classe)
                db.session.commit()
                flash(f"Classe '{nom}' supprimée.", "success")

            return redirect(url_for('classe.add_classe'))

        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de l'opération.", "error")
            return redirect(url_for('classe.add_classe'))

    # Charger les classes avec statistiques
    classes = Classe.query.filter_by(ecole_id=session['ecole_id']).all()
    for classe in classes:
        classe.nb_eleves = Eleve.query.filter_by(classe_id=classe.id).count()
        classe.nb_matieres = Matiere.query.filter_by(classe_id=classe.id).count()

    return render_template('add_classe.html', classes=classes)


@classe_bp.route('/add_classe_ar', methods=['GET', 'POST'])
@login_required
def add_classe_ar():
    """Gestion des classes pour les écoles franco-arabes (ajout, modification, suppression)"""
    # 🔒 Vérifier que l'école est bien franco-arabe
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé à cette page.", "error")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        classe_id = request.form.get('classe_id')

        try:
            if action == 'add':
                nom = request.form.get('nom', '').strip()
                annee_scolaire = request.form.get('annee_scolaire', '2025-2026')
                
                if not nom:
                    flash("اسم القسم إلزامي.", "error")
                    return redirect(url_for('classe.add_classe_ar'))
                
                # Vérifier les doublons
                if Classe.query.filter_by(ecole_id=session['ecole_id'], nom=nom).first():
                    flash("قسم بهذا الاسم موجود مسبقاً.", "warning")
                    return redirect(url_for('classe.add_classe_ar'))
                
                classe = Classe(
                    nom=nom,
                    ecole_id=session['ecole_id'],
                    annee_scolaire=annee_scolaire
                )
                db.session.add(classe)
                db.session.commit()
                flash(f"تمت إضافة القسم '{nom}' بنجاح!", "success")

            elif action == 'edit' and classe_id:
                classe = Classe.query.get_or_404(classe_id)
                if classe.ecole_id != session['ecole_id']:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('classe.add_classe_ar'))
                
                nom = request.form.get('nom', '').strip()
                annee_scolaire = request.form.get('annee_scolaire', '2025-2026')
                
                if not nom:
                    flash("اسم القسم إلزامي.", "error")
                    return redirect(url_for('classe.add_classe_ar'))
                
                # Vérifier les doublons (sauf pour cette classe)
                existing = Classe.query.filter(
                    Classe.ecole_id == session['ecole_id'],
                    Classe.nom == nom,
                    Classe.id != classe.id
                ).first()
                
                if existing:
                    flash("قسم بهذا الاسم موجود مسبقاً.", "warning")
                    return redirect(url_for('classe.add_classe_ar'))
                
                classe.nom = nom
                classe.annee_scolaire = annee_scolaire
                db.session.commit()
                flash(f"تم تعديل القسم '{nom}'.", "success")

            elif action == 'delete' and classe_id:
                classe = Classe.query.get_or_404(classe_id)
                if classe.ecole_id != session['ecole_id']:
                    flash("إجراء غير مصرح به.", "error")
                    return redirect(url_for('classe.add_classe_ar'))
                
                nom = classe.nom
                nb_eleves = Eleve.query.filter_by(classe_id=classe.id).count()
                nb_matieres = Matiere.query.filter_by(classe_id=classe.id).count()
                
                if nb_eleves > 0 or nb_matieres > 0:
                    flash(f"لا يمكن حذف القسم '{nom}'. يحتوي على {nb_eleves} تلميذ(ة) و {nb_matieres} مادة(ات).", "warning")
                    return redirect(url_for('classe.add_classe_ar'))
                
                db.session.delete(classe)
                db.session.commit()
                flash(f"تم حذف القسم '{nom}'.", "success")

            return redirect(url_for('classe.add_classe_ar'))

        except Exception as e:
            db.session.rollback()
            flash("حدث خطأ أثناء المعالجة.", "error")
            return redirect(url_for('classe.add_classe_ar'))

    # Charger les classes avec statistiques
    classes = Classe.query.filter_by(ecole_id=session['ecole_id']).all()
    for classe in classes:
        classe.nb_eleves = Eleve.query.filter_by(classe_id=classe.id).count()
        classe.nb_matieres = Matiere.query.filter_by(classe_id=classe.id).count()

    return render_template('add_classe_ar.html', classes=classes)