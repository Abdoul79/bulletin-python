"""
routes/absences.py
Blueprint de gestion des absences
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from models import db, Eleve, Classe, Absence, Ecole
from datetime import date, datetime, timedelta
from functools import wraps
from collections import defaultdict

absences_bp = Blueprint('absences', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'ecole_id' not in session:
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


# ══════════════════════════════════════════════════════════════
#  PAGE PRINCIPALE — FEUILLE D'ABSENCES
# ══════════════════════════════════════════════════════════════

@absences_bp.route('/classe/<int:classe_id>/absences', methods=['GET', 'POST'])
@login_required
def feuille_absences(classe_id):
    ecole  = get_ecole()
    classe = Classe.query.get_or_404(classe_id)

    if classe.ecole_id != ecole.id:
        abort(403)

    # Date sélectionnée (aujourd'hui par défaut)
    date_str = request.args.get('date') or request.form.get('date')
    try:
        date_sel = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        date_sel = date.today()

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False)\
                        .order_by(Eleve.nom, Eleve.prenom).all()

    # ── POST : enregistrer les absences ──────────────────#
    if request.method == 'POST':
        for eleve in eleves:
            matin      = f'matin_{eleve.id}'      in request.form
            apres_midi = f'apres_midi_{eleve.id}' in request.form
            justifiee  = f'justifie_{eleve.id}'   in request.form
            motif      = request.form.get(f'motif_{eleve.id}', '').strip() or None

            # Chercher une absence existante pour ce jour
            absence = Absence.query.filter_by(
                eleve_id=eleve.id,
                classe_id=classe_id,
                date_absence=date_sel
            ).first()

            if matin or apres_midi:
                if absence:
                    absence.matin      = matin
                    absence.apres_midi = apres_midi
                    absence.justifiee  = justifiee
                    absence.motif      = motif
                else:
                    absence = Absence(
                        eleve_id=eleve.id,
                        classe_id=classe_id,
                        date_absence=date_sel,
                        matin=matin,
                        apres_midi=apres_midi,
                        justifiee=justifiee,
                        motif=motif
                    )
                    db.session.add(absence)
            else:
                # Plus d'absence → supprimer si elle existait
                if absence:
                    db.session.delete(absence)

        db.session.commit()
        flash(f'Absences du {date_sel.strftime("%d/%m/%Y")} enregistrées.', 'success')
        return redirect(url_for('absences.feuille_absences',
                                classe_id=classe_id,
                                date=date_sel.isoformat()))

    # ── GET : charger les absences du jour ───────────────
    absences_jour = {
        a.eleve_id: a
        for a in Absence.query.filter_by(
            classe_id=classe_id,
            date_absence=date_sel
        ).all()
    }

    # Navigation semaine
    lundi = date_sel - timedelta(days=date_sel.weekday())
    semaine = [lundi + timedelta(days=i) for i in range(6)]  # lun → sam

    # Stats du mois pour chaque élève
    debut_mois = date_sel.replace(day=1)
    fin_mois   = (debut_mois.replace(month=debut_mois.month % 12 + 1, day=1)
                  if debut_mois.month < 12
                  else debut_mois.replace(year=debut_mois.year + 1, month=1, day=1))

    stats_mois = {}
    for eleve in eleves:
        abs_mois = Absence.query.filter(
            Absence.eleve_id  == eleve.id,
            Absence.classe_id == classe_id,
            Absence.date_absence >= debut_mois,
            Absence.date_absence <  fin_mois
        ).all()
        total_dj = sum(a.nb_demi_journees for a in abs_mois)
        stats_mois[eleve.id] = {
            'total_demi':   total_dj,
            'total_jours':  total_dj / 2,
            'justifiees':   sum(1 for a in abs_mois if a.justifiee),
            'injustifiees': sum(1 for a in abs_mois if not a.justifiee),
        }

    template = 'absences_ar.html' if is_arabe(ecole) else 'absences.html'
    return render_template(template,
        ecole=ecole, classe=classe, eleves=eleves,
        date_sel=date_sel, semaine=semaine,
        absences_jour=absences_jour, stats_mois=stats_mois,
        aujourd_hui=date.today()
    )


# ══════════════════════════════════════════════════════════════
#  BILAN DES ABSENCES — vue mensuelle/annuelle
# ══════════════════════════════════════════════════════════════

@absences_bp.route('/classe/<int:classe_id>/absences/bilan')
@login_required
def bilan_absences(classe_id):
    ecole  = get_ecole()
    classe = Classe.query.get_or_404(classe_id)

    if classe.ecole_id != ecole.id:
        abort(403)

    eleves = Eleve.query.filter_by(classe_id=classe_id, archive=False )\
                        .order_by(Eleve.nom, Eleve.prenom).all()

    # Toutes les absences de la classe
    toutes = Absence.query.filter_by(classe_id=classe_id)\
                          .order_by(Absence.date_absence).all()

    # Construire le bilan par élève
    bilan = {}
    for eleve in eleves:
        abs_eleve = [a for a in toutes if a.eleve_id == eleve.id]
        total_dj  = sum(a.nb_demi_journees for a in abs_eleve)
        bilan[eleve.id] = {
            'eleve':        eleve,
            'total_demi':   total_dj,
            'total_jours':  total_dj / 2,
            'justifiees':   sum(a.nb_demi_journees for a in abs_eleve if a.justifiee),
            'injustifiees': sum(a.nb_demi_journees for a in abs_eleve if not a.justifiee),
            'jours_entiers': sum(1 for a in abs_eleve if a.journee_entiere),
            'historique':   abs_eleve,
        }

    template = 'bilan_absences_ar.html' if is_arabe(ecole) else 'bilan_absences.html'
    return render_template(template,
        ecole=ecole, classe=classe,
        eleves=eleves, bilan=bilan
    )