from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Classe, Matiere, Eleve, Note, Ecole
from utils import login_required, validate_note, get_trimestre_choices

notes_bp = Blueprint('notes', __name__, url_prefix='/ecole')


# === Route HTML française ===
@notes_bp.route('/saisir_notes/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def saisir_notes(classe_id):
    """Saisie et gestion des notes"""
    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    matieres = Matiere.query.filter_by(classe_id=classe_id).order_by(Matiere.nom).all()
    eleves = Eleve.query.filter_by(classe_id=classe_id).order_by(Eleve.nom, Eleve.prenom).all()

    if not matieres:
        flash("Ajoutez d'abord des matières pour cette classe.", "warning")
        return redirect(url_for('matiere.add_matiere', classe_id=classe_id))
    if not eleves:
        flash("Ajoutez d'abord des élèves pour cette classe.", "warning")
        return redirect(url_for('eleve.add_eleve', classe_id=classe_id))

    if request.method == 'POST':
        trimestre = request.form.get('trimestre', 'T1')
        notes_saisies = 0
        notes_modifiees = 0
        erreurs = 0
        try:
            for eleve in eleves:
                for matiere in matieres:
                    note_key = f"note_{eleve.id}_{matiere.id}"
                    if note_key in request.form:
                        note_value = request.form[note_key].strip()
                        if note_value:
                            is_valid, note_float = validate_note(note_value)
                            if is_valid:
                                existing = Note.query.filter_by(
                                    eleve_id=eleve.id,
                                    matiere_id=matiere.id,
                                    trimestre=trimestre,
                                    statut='active'
                                ).first()
                                if existing:
                                    existing.note = note_float
                                    notes_modifiees += 1
                                else:
                                    note = Note(
                                        eleve_id=eleve.id,
                                        matiere_id=matiere.id,
                                        note=note_float,
                                        trimestre=trimestre,
                                        statut='active'
                                    )
                                    db.session.add(note)
                                    notes_saisies += 1
                            else:
                                erreurs += 1
                                flash(f"Note invalide pour {eleve.prenom} {eleve.nom} en {matiere.nom} (doit être entre 0 et 20)", "error")
            db.session.commit()
            messages = []
            if notes_saisies > 0:
                messages.append(f"{notes_saisies} nouvelle(s) note(s) ajoutée(s)")
            if notes_modifiees > 0:
                messages.append(f"{notes_modifiees} note(s) modifiée(s)")
            if erreurs > 0:
                messages.append(f"{erreurs} erreur(s) de saisie")
            if messages:
                flash(" | ".join(messages), "success" if erreurs == 0 else "warning")
            return redirect(url_for('notes.saisir_notes', classe_id=classe_id, trimestre=trimestre))
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de la sauvegarde des notes.", "error")

    notes_enregistrees = db.session.query(Note)\
        .join(Eleve).join(Matiere)\
        .filter(Eleve.classe_id == classe_id)\
        .order_by(Note.date_saisie.desc())\
        .limit(50)\
        .all()

    return render_template(
        'saisir_notes.html',
        classe=classe,
        matieres=matieres,
        eleves=eleves,
        notes_dict={},
        trimestre_actuel=None,
        notes_enregistrees=notes_enregistrees,
        trimestre_choices=get_trimestre_choices()
    )


# === Route HTML arabe ===
@notes_bp.route('/saisir_notes_ar/<int:classe_id>', methods=['GET', 'POST'])
@login_required
def saisir_notes_ar(classe_id):
    """Saisie et gestion des notes pour les écoles franco-arabes"""
    ecole = Ecole.query.get(session['ecole_id'])
    if not ecole or ecole.type_ecole != 'franco-arabe':
        flash("Accès non autorisé à cette page.", "error")
        return redirect(url_for('main.dashboard'))

    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard_ar'))

    matieres = Matiere.query.filter_by(classe_id=classe_id).order_by(Matiere.nom).all()
    eleves = Eleve.query.filter_by(classe_id=classe_id).order_by(Eleve.nom, Eleve.prenom).all()

    if not matieres:
        flash("أضف المواد أولاً لهذا القسم.", "warning")
        return redirect(url_for('matiere.add_matiere_ar', classe_id=classe_id))
    if not eleves:
        flash("أضف التلاميذ أولاً لهذا القسم.", "warning")
        return redirect(url_for('eleve.add_eleve_ar', classe_id=classe_id))

    if request.method == 'POST':
        trimestre = request.form.get('trimestre', 'T1')
        notes_saisies = 0
        notes_modifiees = 0
        erreurs = 0
        try:
            for eleve in eleves:
                for matiere in matieres:
                    note_key = f"note_{eleve.id}_{matiere.id}"
                    if note_key in request.form:
                        note_value = request.form[note_key].strip()
                        if note_value:
                            is_valid, note_float = validate_note(note_value)
                            if is_valid:
                                existing = Note.query.filter_by(
                                    eleve_id=eleve.id,
                                    matiere_id=matiere.id,
                                    trimestre=trimestre,
                                    statut='active'
                                ).first()
                                if existing:
                                    existing.note = note_float
                                    notes_modifiees += 1
                                else:
                                    note = Note(
                                        eleve_id=eleve.id,
                                        matiere_id=matiere.id,
                                        note=note_float,
                                        trimestre=trimestre,
                                        statut='active'
                                    )
                                    db.session.add(note)
                                    notes_saisies += 1
                            else:
                                erreurs += 1
                                flash(f"نقطة غير صحيحة لتلميذ {eleve.prenom} {eleve.nom} في مادة {matiere.nom} (يجب أن تكون بين 0 و 20)", "error")
            db.session.commit()
            messages = []
            if notes_saisies > 0:
                messages.append(f"تمت إضافة {notes_saisies} نقطة(ات) جديدة")
            if notes_modifiees > 0:
                messages.append(f"تم تعديل {notes_modifiees} نقطة(ات)")
            if erreurs > 0:
                messages.append(f"{erreurs} خطأ(أخطاء) في الإدخال")
            if messages:
                flash(" | ".join(messages), "success" if erreurs == 0 else "warning")
            return redirect(url_for('notes.saisir_notes_ar', classe_id=classe_id, trimestre=trimestre))
        except Exception as e:
            db.session.rollback()
            flash("حدث خطأ أثناء حفظ النقاط.", "error")

    notes_enregistrees = db.session.query(Note)\
        .join(Eleve).join(Matiere)\
        .filter(Eleve.classe_id == classe_id)\
        .order_by(Note.date_saisie.desc())\
        .limit(50)\
        .all()

    return render_template(
        'saisir_notes_ar.html',
        classe=classe,
        matieres=matieres,
        eleves=eleves,
        notes_dict={},
        trimestre_actuel=None,
        notes_enregistrees=notes_enregistrees,
        trimestre_choices=get_trimestre_choices()
    )


# === Routes AJAX (UNE SEULE FOIS, partagées par les deux interfaces) ===

@notes_bp.route('/modifier_note', methods=['POST'])
@login_required
def modifier_note():
    try:
        data = request.get_json()
        note_id = data.get('note_id')
        nouvelle_note = data.get('nouvelle_note')
        is_valid, note_value = validate_note(nouvelle_note)
        if not is_valid:
            return jsonify({'success': False, 'message': 'يجب أن تكون النقطة بين 0 و 20'})
        note = Note.query.get_or_404(note_id)
        if not _verify_note_ownership(note):
            return jsonify({'success': False, 'message': 'غير مصرح به'})
        ancienne_note = note.note
        note.note = note_value
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'تم تعديل النقطة من {ancienne_note} إلى {note_value}',
            'nouvelle_note': note_value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@notes_bp.route('/suspendre_note', methods=['POST'])
@login_required
def suspendre_note():
    try:
        data = request.get_json()
        note_id = data.get('note_id')
        note = Note.query.get_or_404(note_id)
        if not _verify_note_ownership(note):
            return jsonify({'success': False, 'message': 'غير مصرح به'})
        note.statut = 'suspendue'
        db.session.commit()
        return jsonify({'success': True, 'message': 'النقطة معلقة (لن تؤخذ بعين الاعتبار في الحساب)'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@notes_bp.route('/activer_note', methods=['POST'])
@login_required
def activer_note():
    try:
        data = request.get_json()
        note_id = data.get('note_id')
        note = Note.query.get_or_404(note_id)
        if not _verify_note_ownership(note):
            return jsonify({'success': False, 'message': 'غير مصرح به'})
        note.statut = 'active'
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم تفعيل النقطة'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@notes_bp.route('/supprimer_note', methods=['POST'])
@login_required
def supprimer_note():
    try:
        data = request.get_json()
        note_id = data.get('note_id')
        note = Note.query.get_or_404(note_id)
        if not _verify_note_ownership(note):
            return jsonify({'success': False, 'message': 'غير مصرح به'})
        eleve_nom = f"{note.eleve.prenom} {note.eleve.nom}"
        matiere_nom = note.matiere.nom
        note_valeur = note.note
        db.session.delete(note)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'تم حذف النقطة نهائياً: {eleve_nom} - {matiere_nom} ({note_valeur}/20)'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@notes_bp.route('/supprimer_toutes_notes', methods=['POST'])
@login_required
def supprimer_toutes_notes():
    try:
        data = request.get_json()
        classe_id = data.get('classe_id')
        if not classe_id:
            return jsonify({'success': False, 'message': 'معرف القسم مفقود'})
        classe = Classe.query.get_or_404(classe_id)
        if classe.ecole_id != session['ecole_id']:
            return jsonify({'success': False, 'message': 'غير مصرح به'})
        eleves_ids = [eleve.id for eleve in Eleve.query.filter_by(classe_id=classe_id).all()]
        if not eleves_ids:
            return jsonify({'success': False, 'message': 'لا يوجد تلاميذ في هذا القسم'})
        count = Note.query.filter(Note.eleve_id.in_(eleves_ids)).count()
        if count == 0:
            return jsonify({'success': False, 'message': 'لا توجد نقاط للحذف'})
        Note.query.filter(Note.eleve_id.in_(eleves_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'تم حذف {count} نقطة(ات) نهائياً من القسم {classe.nom}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# === Route de lecture seule (optionnelle, non dupliquée) ===
@notes_bp.route('/voir_notes/<int:classe_id>')
@login_required
def voir_notes(classe_id):
    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != session['ecole_id']:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('main.dashboard'))

    trimestre = request.args.get('trimestre', 'T1')
    notes = db.session.query(Note)\
        .join(Eleve).join(Matiere)\
        .filter(Eleve.classe_id == classe_id)\
        .filter(Note.trimestre == trimestre)\
        .filter(Note.statut == 'active')\
        .order_by(Eleve.nom, Eleve.prenom, Matiere.nom)\
        .all()

    notes_par_eleve = {}
    for note in notes:
        eleve_key = f"{note.eleve.nom} {note.eleve.prenom}"
        if eleve_key not in notes_par_eleve:
            notes_par_eleve[eleve_key] = {'eleve': note.eleve, 'notes': [], 'moyenne': 0}
        notes_par_eleve[eleve_key]['notes'].append(note)

    for eleve_data in notes_par_eleve.values():
        if eleve_data['notes']:
            total = sum(n.note for n in eleve_data['notes'])
            eleve_data['moyenne'] = round(total / len(eleve_data['notes']), 2)

    return render_template(
        'voir_notes.html',
        classe=classe,
        notes_par_eleve=notes_par_eleve,
        trimestre_actuel=trimestre,
        trimestre_choices=get_trimestre_choices()
    )


# === Fonction utilitaire (une seule fois) ===
def _verify_note_ownership(note):
    classe = db.session.get(Classe, note.eleve.classe_id)
    return classe and classe.ecole_id == session.get('ecole_id')

