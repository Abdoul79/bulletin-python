"""
routes/paiements.py
Blueprint de gestion des paiements de scolarité
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, Eleve, Classe, Scolarite, Paiement, Ecole
from datetime import datetime
from functools import wraps
from flask import session

paiements_bp = Blueprint('paiements', __name__)


# ── Helper: vérifier connexion ──────────────────────────────
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
    return ecole.type_ecole in ('arabe', 'franco_arabe')


# ══════════════════════════════════════════════════════════════
#  DÉFINIR / MODIFIER LES FRAIS D'UN ÉLÈVE
# ══════════════════════════════════════════════════════════════

@paiements_bp.route('/eleve/<int:eleve_id>/scolarite/definir', methods=['GET', 'POST'])
@login_required
def definir_scolarite(eleve_id):
    ecole  = get_ecole()
    eleve  = Eleve.query.get_or_404(eleve_id)
    classe = Classe.query.get(eleve.classe_id)

    # Vérifier que l'élève appartient à l'école
    if classe.ecole_id != ecole.id:
        abort(403)

    # Chercher scolarité existante pour l'année en cours
    scolarite = Scolarite.query.filter_by(
        eleve_id=eleve_id,
        annee_scolaire=classe.annee_scolaire
    ).first()

    if request.method == 'POST':
        montant = float(request.form.get('montant_total', 0))
        if scolarite:
            scolarite.montant_total = montant
        else:
            scolarite = Scolarite(
                eleve_id=eleve_id,
                classe_id=classe.id,
                montant_total=montant,
                annee_scolaire=classe.annee_scolaire
            )
            db.session.add(scolarite)
        db.session.commit()
        flash('Frais de scolarité enregistrés avec succès.', 'success')
        return redirect(url_for('paiements.voir_paiements', eleve_id=eleve_id))

    template = 'definir_scolarite_ar.html' if is_arabe(ecole) else 'definir_scolarite.html'
    return render_template(template, ecole=ecole, eleve=eleve, classe=classe, scolarite=scolarite)


# ══════════════════════════════════════════════════════════════
#  VOIR LES PAIEMENTS D'UN ÉLÈVE + AJOUTER UN PAIEMENT
# ══════════════════════════════════════════════════════════════

@paiements_bp.route('/eleve/<int:eleve_id>/paiements', methods=['GET', 'POST'])
@login_required
def voir_paiements(eleve_id):
    ecole  = get_ecole()
    eleve  = Eleve.query.get_or_404(eleve_id)
    classe = Classe.query.get(eleve.classe_id)

    if classe.ecole_id != ecole.id:
        abort(403)

    scolarite = Scolarite.query.filter_by(
        eleve_id=eleve_id,
        annee_scolaire=classe.annee_scolaire
    ).first()

    if request.method == 'POST':
        if not scolarite:
            flash('Veuillez d\'abord définir les frais de scolarité.', 'warning')
            return redirect(url_for('paiements.definir_scolarite', eleve_id=eleve_id))

        montant = float(request.form.get('montant', 0))
        if montant <= 0:
            flash('Montant invalide.', 'danger')
        elif montant > scolarite.montant_restant + 0.01:
            flash(f'Montant dépasse le reste dû ({scolarite.montant_restant:,.0f} FCFA).', 'danger')
        else:
            paiement = Paiement(
                scolarite_id=scolarite.id,
                montant=montant,
                mode_paiement=request.form.get('mode_paiement', 'espèces'),
                notes=request.form.get('notes', ''),
                encaisseur=request.form.get('encaisseur', ''),
                date_paiement=datetime.utcnow()
            )
            db.session.add(paiement)
            db.session.commit()
            flash('Paiement enregistré avec succès !', 'success')
            return redirect(url_for('paiements.recu_paiement', paiement_id=paiement.id))

    paiements_liste = []
    if scolarite:
        paiements_liste = Paiement.query.filter_by(scolarite_id=scolarite.id)\
                                        .order_by(Paiement.date_paiement.desc()).all()

    template = 'paiements_ar.html' if is_arabe(ecole) else 'paiements.html'
    return render_template(template,
        ecole=ecole, eleve=eleve, classe=classe,
        scolarite=scolarite, paiements=paiements_liste
    )


# ══════════════════════════════════════════════════════════════
#  REÇU DE PAIEMENT
# ══════════════════════════════════════════════════════════════

@paiements_bp.route('/paiement/<int:paiement_id>/recu')
@login_required
def recu_paiement(paiement_id):
    ecole    = get_ecole()
    paiement = Paiement.query.get_or_404(paiement_id)
    scolarite = paiement.scolarite
    eleve    = scolarite.eleve
    classe   = scolarite.classe

    if classe.ecole_id != ecole.id:
        abort(403)

    template = 'recu_paiement_ar.html' if is_arabe(ecole) else 'recu_paiement.html'
    return render_template(template,
        ecole=ecole, paiement=paiement,
        scolarite=scolarite, eleve=eleve, classe=classe
    )


# ══════════════════════════════════════════════════════════════
#  PAIEMENTS PAR CLASSE
# ══════════════════════════════════════════════════════════════

@paiements_bp.route('/classe/<int:classe_id>/paiements')
@login_required
def paiements_classe(classe_id):
    ecole  = get_ecole()
    classe = Classe.query.get_or_404(classe_id)

    if classe.ecole_id != ecole.id:
        abort(403)

    # Récupérer toutes les scolarités de la classe
    scolarites = Scolarite.query.filter_by(
        classe_id=classe_id,
        annee_scolaire=classe.annee_scolaire
    ).all()

    # Stats globales classe
    total_attendu = sum(s.montant_total for s in scolarites)
    total_paye    = sum(s.montant_paye for s in scolarites)
    total_restant = sum(s.montant_restant for s in scolarites)
    nb_soldes     = sum(1 for s in scolarites if s.est_solde)

    template = 'paiements_classe_ar.html' if is_arabe(ecole) else 'paiements_classe.html'
    return render_template(template,
        ecole=ecole, classe=classe, scolarites=scolarites,
        total_attendu=total_attendu, total_paye=total_paye,
        total_restant=total_restant, nb_soldes=nb_soldes
    )


# ══════════════════════════════════════════════════════════════
#  SUPPRIMER UN PAIEMENT (admin seulement)
# ══════════════════════════════════════════════════════════════

@paiements_bp.route('/paiement/<int:paiement_id>/supprimer', methods=['POST'])
@login_required
def supprimer_paiement(paiement_id):
    ecole    = get_ecole()
    paiement = Paiement.query.get_or_404(paiement_id)
    scolarite = paiement.scolarite
    eleve_id  = scolarite.eleve_id

    if scolarite.classe.ecole_id != ecole.id:
        abort(403)

    db.session.delete(paiement)
    db.session.commit()
    flash('Paiement supprimé.', 'info')
    return redirect(url_for('paiements.voir_paiements', eleve_id=eleve_id))