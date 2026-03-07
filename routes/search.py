from flask import Blueprint, request, jsonify, session
from models import db, Classe, Eleve, Matiere, Note, Ecole
from utils import login_required
from sqlalchemy import or_, and_

search_bp = Blueprint('search', __name__, url_prefix='/api/search')


@search_bp.route('/global')
@login_required
def global_search():
    """Recherche globale dans toutes les données de l'école"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    classe_id = request.args.get('class_id')
    trimestre = request.args.get('trimester')
    min_grade = request.args.get('min_grade', type=float)
    max_grade = request.args.get('max_grade', type=float)
    
    if len(query) < 2:
        return jsonify({'results': [], 'count': 0})
    
    ecole_id = session['ecole_id']
    results = []
    
    try:
        # Recherche d'élèves
        if search_type in ['all', 'students']:
            students = db.session.query(Eleve)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .filter(or_(
                    Eleve.prenom.ilike(f'%{query}%'),
                    Eleve.nom.ilike(f'%{query}%'),
                    (Eleve.prenom + ' ' + Eleve.nom).ilike(f'%{query}%')
                ))
            
            if classe_id:
                students = students.filter(Eleve.classe_id == classe_id)
            
            for student in students.limit(20).all():
                results.append({
                    'type': 'student',
                    'id': student.id,
                    'title': f"{student.prenom} {student.nom}",
                    'subtitle': f"Classe: {student.classe.nom}",
                    'url': f"/ecole/classe/{student.classe_id}",
                    'data': {
                        'student_id': student.id,
                        'class_id': student.classe_id,
                        'class_name': student.classe.nom
                    }
                })
        
        # Recherche de matières
        if search_type in ['all', 'subjects']:
            subjects = db.session.query(Matiere)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .filter(Matiere.nom.ilike(f'%{query}%'))
            
            if classe_id:
                subjects = subjects.filter(Matiere.classe_id == classe_id)
            
            for subject in subjects.limit(20).all():
                results.append({
                    'type': 'subject',
                    'id': subject.id,
                    'title': subject.nom,
                    'subtitle': f"Classe: {subject.classe.nom} - Prof: {subject.professeur or 'N/A'}",
                    'url': f"/ecole/add_matiere/{subject.classe_id}",
                    'data': {
                        'subject_id': subject.id,
                        'class_id': subject.classe_id,
                        'class_name': subject.classe.nom,
                        'teacher': subject.professeur
                    }
                })
        
        # Recherche de notes
        if search_type in ['all', 'notes']:
            notes_query = db.session.query(Note)\
                .join(Eleve)\
                .join(Matiere)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .filter(or_(
                    Eleve.prenom.ilike(f'%{query}%'),
                    Eleve.nom.ilike(f'%{query}%'),
                    Matiere.nom.ilike(f'%{query}%'),
                    (Eleve.prenom + ' ' + Eleve.nom).ilike(f'%{query}%')
                ))
            
            # Filtres avancés pour les notes
            if classe_id:
                notes_query = notes_query.filter(Classe.id == classe_id)
            
            if trimestre:
                notes_query = notes_query.filter(Note.trimestre == trimestre)
            
            if min_grade is not None:
                notes_query = notes_query.filter(Note.note >= min_grade)
            
            if max_grade is not None:
                notes_query = notes_query.filter(Note.note <= max_grade)
            
            for note in notes_query.limit(50).all():
                results.append({
                    'type': 'note',
                    'id': note.id,
                    'title': f"{note.eleve.prenom} {note.eleve.nom} - {note.matiere.nom}",
                    'subtitle': f"Note: {note.note}/20 - {note.trimestre} - Classe: {note.eleve.classe.nom}",
                    'url': f"/ecole/saisir_notes/{note.eleve.classe_id}",
                    'data': {
                        'note_id': note.id,
                        'student_name': f"{note.eleve.prenom} {note.eleve.nom}",
                        'subject_name': note.matiere.nom,
                        'grade': note.note,
                        'trimester': note.trimestre,
                        'status': note.statut,
                        'class_id': note.eleve.classe_id,
                        'class_name': note.eleve.classe.nom
                    }
                })
        
        # Trier les résultats par pertinence (élèves d'abord, puis par nom)
        results.sort(key=lambda x: (
            0 if x['type'] == 'student' else 1 if x['type'] == 'subject' else 2,
            x['title'].lower()
        ))
        
        return jsonify({
            'results': results[:50],  # Limiter à 50 résultats
            'count': len(results),
            'query': query,
            'filters': {
                'type': search_type,
                'class_id': classe_id,
                'trimester': trimestre,
                'min_grade': min_grade,
                'max_grade': max_grade
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'results': [],
            'count': 0
        }), 500


@search_bp.route('/suggestions')
@login_required
def search_suggestions():
    """Suggestions de recherche basées sur les données existantes"""
    query = request.args.get('q', '').strip().lower()
    
    if len(query) < 1:
        return jsonify({'suggestions': []})
    
    ecole_id = session['ecole_id']
    suggestions = set()
    
    try:
        # Suggestions d'élèves
        students = db.session.query(Eleve.prenom, Eleve.nom)\
            .join(Classe)\
            .filter(Classe.ecole_id == ecole_id)\
            .filter(or_(
                Eleve.prenom.ilike(f'{query}%'),
                Eleve.nom.ilike(f'{query}%')
            ))\
            .limit(10).all()
        
        for student in students:
            suggestions.add(f"{student.prenom} {student.nom}")
        
        # Suggestions de matières
        subjects = db.session.query(Matiere.nom)\
            .join(Classe)\
            .filter(Classe.ecole_id == ecole_id)\
            .filter(Matiere.nom.ilike(f'{query}%'))\
            .distinct()\
            .limit(10).all()
        
        for subject in subjects:
            suggestions.add(subject.nom)
        
        # Suggestions de classes
        classes = db.session.query(Classe.nom)\
            .filter(Classe.ecole_id == ecole_id)\
            .filter(Classe.nom.ilike(f'{query}%'))\
            .limit(5).all()
        
        for classe in classes:
            suggestions.add(classe.nom)
        
        return jsonify({
            'suggestions': sorted(list(suggestions))[:15]
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'suggestions': []
        }), 500


@search_bp.route('/quick-stats')
@login_required
def quick_stats():
    """Statistiques rapides pour la recherche"""
    ecole_id = session['ecole_id']
    
    try:
        stats = {
            'total_students': db.session.query(Eleve)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .count(),
            
            'total_subjects': db.session.query(Matiere)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .count(),
            
            'total_notes': db.session.query(Note)\
                .join(Eleve)\
                .join(Classe)\
                .filter(Classe.ecole_id == ecole_id)\
                .count(),
            
            'classes': [
                {
                    'id': c.id,
                    'name': c.nom,
                    'students_count': len(c.eleves)
                }
                for c in Classe.query.filter_by(ecole_id=ecole_id).all()
            ]
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'stats': {}
        }), 500