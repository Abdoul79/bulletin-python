"""
routes/analytics.py
Blueprint analytique — statistiques avancées EduBulletin
"""

from flask import Blueprint, render_template, abort, session
from models import db, Ecole, Classe, Eleve, Matiere, Note
from functools import wraps
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'ecole_id' not in session:
            from flask import redirect, url_for
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated


def get_ecole():
    return Ecole.query.get(session['ecole_id'])


def is_arabe(ecole):
    lang = session.get('lang') or session.get('langue') or session.get('language') or ''
    if lang in ('ar', 'arabic', 'arabe'):
        return True
    return ecole.type_ecole in ('arabe', 'franco_arabe', 'franco-arabe')


def _moyenne_notes(notes_list):
    vals = [n for n in notes_list if n is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _mention(moy):
    if moy >= 16: return 'Très bien'
    if moy >= 14: return 'Bien'
    if moy >= 12: return 'Assez bien'
    if moy >= 10: return 'Passable'
    return 'Insuffisant'


# ══════════════════════════════════════════════════════════════
#  DASHBOARD ANALYTIQUE GLOBAL
# ══════════════════════════════════════════════════════════════

@analytics_bp.route('/analytics')
@login_required
def dashboard_analytics():
    ecole   = get_ecole()
    classes = Classe.query.filter_by(ecole_id=ecole.id).all()

    stats_classes = []

    for classe in classes:
        eleves  = Eleve.query.filter_by(classe_id=classe.id).all()
        if not eleves:
            continue

        matieres = Matiere.query.filter_by(classe_id=classe.id).all()

        # Moyennes par trimestre pour la classe
        moyennes_trim = {}
        for trim in ['T1', 'T2', 'T3']:
            notes_trim = Note.query.join(Eleve).filter(
                Eleve.classe_id == classe.id,
                Note.trimestre == trim
            ).with_entities(Note.valeur).all()
            vals = [n.valeur for n in notes_trim if n.valeur is not None]
            moyennes_trim[trim] = round(sum(vals) / len(vals), 2) if vals else 0.0

        # Moyenne annuelle classe
        toutes_notes = Note.query.join(Eleve).filter(
            Eleve.classe_id == classe.id
        ).with_entities(Note.valeur).all()
        vals_all = [n.valeur for n in toutes_notes if n.valeur is not None]
        moy_annuelle = round(sum(vals_all) / len(vals_all), 2) if vals_all else 0.0

        # Taux de réussite (moyenne >= 10)
        eleves_reussis = 0
        for eleve in eleves:
            notes_eleve = Note.query.filter_by(eleve_id=eleve.id).with_entities(Note.valeur).all()
            vals_e = [n.valeur for n in notes_eleve if n.valeur is not None]
            if vals_e and (sum(vals_e) / len(vals_e)) >= 10:
                eleves_reussis += 1

        taux_reussite = round(eleves_reussis / len(eleves) * 100) if eleves else 0

        # Matière la plus faible
        mat_stats = []
        for mat in matieres:
            notes_mat = Note.query.filter_by(matiere_id=mat.id).with_entities(Note.valeur).all()
            vals_m = [n.valeur for n in notes_mat if n.valeur is not None]
            if vals_m:
                mat_stats.append({
                    'nom': mat.nom,
                    'moyenne': round(sum(vals_m) / len(vals_m), 2)
                })
        mat_stats.sort(key=lambda x: x['moyenne'])
        mat_faible = mat_stats[0] if mat_stats else None
        mat_forte  = mat_stats[-1] if mat_stats else None

        # Top 3 élèves
        eleves_moyennes = []
        for eleve in eleves:
            notes_e = Note.query.filter_by(eleve_id=eleve.id).with_entities(Note.valeur).all()
            vals_e = [n.valeur for n in notes_e if n.valeur is not None]
            moy_e = round(sum(vals_e) / len(vals_e), 2) if vals_e else 0.0
            eleves_moyennes.append({'eleve': eleve, 'moyenne': moy_e})
        eleves_moyennes.sort(key=lambda x: x['moyenne'], reverse=True)

        stats_classes.append({
            'classe': classe,
            'nb_eleves': len(eleves),
            'nb_matieres': len(matieres),
            'moyennes_trim': moyennes_trim,
            'moy_annuelle': moy_annuelle,
            'taux_reussite': taux_reussite,
            'eleves_reussis': eleves_reussis,
            'mat_faible': mat_faible,
            'mat_forte': mat_forte,
            'top3': eleves_moyennes[:3],
            'mat_stats': mat_stats,
        })

    # Stats globales école
    total_eleves   = sum(s['nb_eleves'] for s in stats_classes)
    total_reussis  = sum(s['eleves_reussis'] for s in stats_classes)
    taux_global    = round(total_reussis / total_eleves * 100) if total_eleves else 0

    moys_annuelles = [s['moy_annuelle'] for s in stats_classes if s['moy_annuelle'] > 0]
    moy_ecole      = round(sum(moys_annuelles) / len(moys_annuelles), 2) if moys_annuelles else 0.0

    template = 'analytics_ar.html' if is_arabe(ecole) else 'analytics.html'
    return render_template(template,
        ecole=ecole,
        classes=classes,
        stats_classes=stats_classes,
        total_eleves=total_eleves,
        total_reussis=total_reussis,
        taux_global=taux_global,
        moy_ecole=moy_ecole,
    )


# ══════════════════════════════════════════════════════════════
#  ANALYTICS D'UNE CLASSE
# ══════════════════════════════════════════════════════════════

@analytics_bp.route('/analytics/classe/<int:classe_id>')
@login_required
def analytics_classe(classe_id):
    ecole  = get_ecole()
    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != ecole.id:
        abort(403)

    eleves   = Eleve.query.filter_by(classe_id=classe.id).all()
    matieres = Matiere.query.filter_by(classe_id=classe.id).all()

    # Progression de chaque élève sur les 3 trimestres
    eleves_data = []
    for eleve in eleves:
        trim_moyennes = {}
        for trim in ['T1', 'T2', 'T3']:
            notes = Note.query.filter_by(eleve_id=eleve.id, trimestre=trim).with_entities(Note.valeur).all()
            vals  = [n.valeur for n in notes if n.valeur is not None]
            trim_moyennes[trim] = round(sum(vals) / len(vals), 2) if vals else None

        notes_all = Note.query.filter_by(eleve_id=eleve.id).with_entities(Note.valeur).all()
        vals_all  = [n.valeur for n in notes_all if n.valeur is not None]
        moy_ann   = round(sum(vals_all) / len(vals_all), 2) if vals_all else 0.0

        eleves_data.append({
            'eleve': eleve,
            'T1': trim_moyennes['T1'],
            'T2': trim_moyennes['T2'],
            'T3': trim_moyennes['T3'],
            'moy_ann': moy_ann,
            'mention': _mention(moy_ann),
            'admis': moy_ann >= 10,
        })
    eleves_data.sort(key=lambda x: x['moy_ann'], reverse=True)

    # Stats par matière
    matieres_stats = []
    for mat in matieres:
        trim_moys = {}
        for trim in ['T1', 'T2', 'T3']:
            notes = Note.query.filter_by(matiere_id=mat.id, trimestre=trim).with_entities(Note.valeur).all()
            vals  = [n.valeur for n in notes if n.valeur is not None]
            trim_moys[trim] = round(sum(vals) / len(vals), 2) if vals else 0.0

        notes_all = Note.query.filter_by(matiere_id=mat.id).with_entities(Note.valeur).all()
        vals_all  = [n.valeur for n in notes_all if n.valeur is not None]
        moy_mat   = round(sum(vals_all) / len(vals_all), 2) if vals_all else 0.0

        matieres_stats.append({
            'matiere': mat,
            'T1': trim_moys['T1'],
            'T2': trim_moys['T2'],
            'T3': trim_moys['T3'],
            'moyenne': moy_mat,
        })
    matieres_stats.sort(key=lambda x: x['moyenne'])

    # Moyennes de la classe par trimestre
    class_trim = {}
    for trim in ['T1', 'T2', 'T3']:
        notes = Note.query.join(Eleve).filter(
            Eleve.classe_id == classe.id, Note.trimestre == trim
        ).with_entities(Note.valeur).all()
        vals = [n.valeur for n in notes if n.valeur is not None]
        class_trim[trim] = round(sum(vals) / len(vals), 2) if vals else 0.0

    nb_admis  = sum(1 for e in eleves_data if e['admis'])
    nb_recale = len(eleves_data) - nb_admis

    template = 'analytics_classe_ar.html' if is_arabe(ecole) else 'analytics_classe.html'
    return render_template(template,
        ecole=ecole, classe=classe,
        eleves_data=eleves_data,
        matieres_stats=matieres_stats,
        class_trim=class_trim,
        nb_admis=nb_admis,
        nb_recale=nb_recale,
    )


# ══════════════════════════════════════════════════════════════
#  CARTE SCOLAIRE
# ══════════════════════════════════════════════════════════════

@analytics_bp.route('/carte-scolaire/<int:eleve_id>')
@login_required
def carte_scolaire(eleve_id):
    ecole  = get_ecole()
    eleve  = Eleve.query.get_or_404(eleve_id)
    classe = Classe.query.get(eleve.classe_id)
    if classe.ecole_id != ecole.id:
        abort(403)

    template = 'carte_scolaire_ar.html' if is_arabe(ecole) else 'carte_scolaire.html'
    return render_template(template, ecole=ecole, eleve=eleve, classe=classe)


@analytics_bp.route('/cartes-scolaires/classe/<int:classe_id>')
@login_required
def cartes_classe(classe_id):
    """Toutes les cartes d'une classe sur une page pour impression"""
    ecole  = get_ecole()
    classe = Classe.query.get_or_404(classe_id)
    if classe.ecole_id != ecole.id:
        abort(403)
    eleves = Eleve.query.filter_by(classe_id=classe.id).order_by(Eleve.nom).all()

    template = 'cartes_classe_ar.html' if is_arabe(ecole) else 'cartes_classe.html'
    return render_template(template, ecole=ecole, classe=classe, eleves=eleves)


# ══════════════════════════════════════════════════════════════
#  RAPPORT DE FIN D'ANNÉE
# ══════════════════════════════════════════════════════════════

@analytics_bp.route('/rapport-annuel')
@login_required
def rapport_annuel():
    ecole   = get_ecole()
    classes = Classe.query.filter_by(ecole_id=ecole.id).all()

    rapport_classes = []

    for classe in classes:
        eleves   = Eleve.query.filter_by(classe_id=classe.id).all()
        matieres = Matiere.query.filter_by(classe_id=classe.id).all()
        if not eleves:
            continue

        eleves_resultats = []
        for eleve in eleves:
            notes_all = Note.query.filter_by(eleve_id=eleve.id).with_entities(Note.valeur).all()
            vals = [n.valeur for n in notes_all if n.valeur is not None]
            moy  = round(sum(vals) / len(vals), 2) if vals else 0.0

            trim_moys = {}
            for trim in ['T1', 'T2', 'T3']:
                notes_t = Note.query.filter_by(eleve_id=eleve.id, trimestre=trim).with_entities(Note.valeur).all()
                vals_t  = [n.valeur for n in notes_t if n.valeur is not None]
                trim_moys[trim] = round(sum(vals_t) / len(vals_t), 2) if vals_t else 0.0

            eleves_resultats.append({
                'eleve': eleve,
                'moyenne': moy,
                'T1': trim_moys['T1'],
                'T2': trim_moys['T2'],
                'T3': trim_moys['T3'],
                'mention': _mention(moy),
                'admis': moy >= 10,
            })
        eleves_resultats.sort(key=lambda x: x['moyenne'], reverse=True)

        # Rang
        for i, er in enumerate(eleves_resultats):
            er['rang'] = i + 1

        nb_admis    = sum(1 for e in eleves_resultats if e['admis'])
        nb_recales  = len(eleves_resultats) - nb_admis
        taux        = round(nb_admis / len(eleves_resultats) * 100) if eleves_resultats else 0

        # Moy classe
        moys = [e['moyenne'] for e in eleves_resultats if e['moyenne'] > 0]
        moy_classe = round(sum(moys) / len(moys), 2) if moys else 0.0

        # Meilleures / moins bonnes matières
        matieres_bilan = []
        for mat in matieres:
            notes_mat = Note.query.filter_by(matiere_id=mat.id).with_entities(Note.valeur).all()
            vals_m = [n.valeur for n in notes_mat if n.valeur is not None]
            matieres_bilan.append({
                'nom': mat.nom,
                'moyenne': round(sum(vals_m) / len(vals_m), 2) if vals_m else 0.0
            })
        matieres_bilan.sort(key=lambda x: x['moyenne'], reverse=True)

        rapport_classes.append({
            'classe': classe,
            'eleves': eleves_resultats,
            'nb_eleves': len(eleves_resultats),
            'nb_admis': nb_admis,
            'nb_recales': nb_recales,
            'taux_reussite': taux,
            'moy_classe': moy_classe,
            'top3': eleves_resultats[:3],
            'matieres_bilan': matieres_bilan,
        })

    # Stats globales école
    total_eleves  = sum(r['nb_eleves'] for r in rapport_classes)
    total_admis   = sum(r['nb_admis']  for r in rapport_classes)
    taux_global   = round(total_admis / total_eleves * 100) if total_eleves else 0
    moys_classes  = [r['moy_classe'] for r in rapport_classes if r['moy_classe'] > 0]
    moy_generale  = round(sum(moys_classes) / len(moys_classes), 2) if moys_classes else 0.0

    template = 'rapport_annuel_ar.html' if is_arabe(ecole) else 'rapport_annuel.html'
    return render_template(template,
        ecole=ecole,
        rapport_classes=rapport_classes,
        total_eleves=total_eleves,
        total_admis=total_admis,
        taux_global=taux_global,
        moy_generale=moy_generale,
    )