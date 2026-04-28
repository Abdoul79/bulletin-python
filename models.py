
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime


import uuid
from datetime import datetime


db = SQLAlchemy()
migrate = Migrate()


class Ecole(db.Model):
    __tablename__ = 'ecole'

    id           = db.Column(db.Integer, primary_key=True)
    nom          = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(100), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)
    directeur    = db.Column(db.String(100))
    adresse      = db.Column(db.Text)
    telephone    = db.Column(db.String(20))
    logo         = db.Column(db.String(100))
    statut       = db.Column(db.String(20), default='actif')
    type_ecole   = db.Column(db.String(20), default='francaise')
    is_active        = db.Column(db.Boolean, default=False, nullable=False)  # ← NOUVEAU
    date_inscription = db.Column(db.DateTime, nullable=True)                 # ← NOUVEAU

    classes           = db.relationship('Classe',        backref='ecole', lazy=True, cascade='all, delete-orphan')
    matricules_utilises = db.relationship('MatriculeUsed', backref='ecole', lazy=True, cascade='all, delete-orphan')


class Classe(db.Model):
    __tablename__ = 'classe'

    id             = db.Column(db.Integer, primary_key=True)
    nom            = db.Column(db.String(50), nullable=False)
    ecole_id       = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False)
    annee_scolaire = db.Column(db.String(9), default='2024-2025')

    eleves   = db.relationship('Eleve',   backref='classe', lazy=True, cascade='all, delete-orphan')
    matieres = db.relationship('Matiere', backref='classe', lazy=True, cascade='all, delete-orphan')

#model absence 
# ═══════════════════════════════════════════════════════
#  AJOUTER DANS models.py — après la classe Eleve
# ═══════════════════════════════════════════════════════

class Absence(db.Model):
    """Enregistrement des absences par demi-journée"""
    __tablename__ = 'absence'

    id           = db.Column(db.Integer, primary_key=True)
    eleve_id     = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    classe_id    = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    date_absence = db.Column(db.Date, nullable=False)
    matin        = db.Column(db.Boolean, default=False)   # avant midi
    apres_midi   = db.Column(db.Boolean, default=False)   # après midi
    justifiee    = db.Column(db.Boolean, default=False)   # absence justifiée
    motif        = db.Column(db.String(200), nullable=True)

    # Relations
    eleve  = db.relationship('Eleve',  backref=db.backref('absences',  lazy=True))
    classe = db.relationship('Classe', backref=db.backref('absences_cl', lazy=True))

    @property
    def journee_entiere(self):
        return self.matin and self.apres_midi

    @property
    def nb_demi_journees(self):
        return int(self.matin) + int(self.apres_midi)

    def __repr__(self):
        return f'<Absence eleve={self.eleve_id} date={self.date_absence}>'

#fin model absence


class Matiere(db.Model):
    """⚠️ Classe manquante — cause de toutes les erreurs"""
    __tablename__ = 'matiere'

    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(100), nullable=False)
    professeur = db.Column(db.String(100), nullable=True)
    jour       = db.Column(db.String(20),  nullable=True)
    heure      = db.Column(db.Time,        nullable=True)
    duree      = db.Column(db.Integer, default=1)
    classe_id  = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)

    notes = db.relationship('Note', backref='matiere', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Matiere {self.nom}>'


class Eleve(db.Model):
    __tablename__ = 'eleve'

    id               = db.Column(db.Integer, primary_key=True)
    matricule        = db.Column(db.String(20), nullable=False)  # unique par école, pas globalement
    prenom           = db.Column(db.String(50), nullable=False)
    nom              = db.Column(db.String(50), nullable=False)
    date_naissance   = db.Column(db.Date)
    sexe             = db.Column(db.String(1))
    classe_id        = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    tuteur           = db.Column(db.String(100))
    telephone_tuteur = db.Column(db.String(15))
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    photo_url = db.Column(db.String(255), nullable=True)

    #notes = db.relationship('Note', backref='eleve', lazy=True, cascade='all, delete-orphan')
    #scolarites = db.relationship('Scolarite', backref='eleve', cascade="all, delete-orphan")
    notes      = db.relationship('Note', backref='eleve', lazy=True, cascade='all, delete-orphan')
    scolarites = db.relationship('Scolarite', back_populates='eleve', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Eleve {self.matricule} - {self.prenom} {self.nom}>'

# commmencer par ici
# ═══════════════════════════════════════════════════════
#  AJOUTER CES DEUX CLASSES DANS models.py
#  (après la classe Eleve)
# ═══════════════════════════════════════════════════════

class Scolarite(db.Model):
    """Frais de scolarité annuels d'un élève"""
    __tablename__ = 'scolarite'

    id             = db.Column(db.Integer, primary_key=True)
    eleve_id       = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    classe_id      = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    montant_total  = db.Column(db.Float, nullable=False, default=0.0)   # Montant annuel total
    annee_scolaire = db.Column(db.String(20), nullable=False)
    date_creation  = db.Column(db.DateTime, default=datetime.utcnow)

    # CASSE CADE
    eleve_id = db.Column(
        db.Integer, 
        db.ForeignKey('eleve.id', ondelete="CASCADE"),  # ← Important !
        nullable=False
    )
    # Relations
    eleve     = db.relationship('Eleve', back_populates='scolarites')
    classe    = db.relationship('Classe', backref='scolarites', lazy=True)
    paiements = db.relationship('Paiement', backref='scolarite', lazy=True,
                                cascade='all, delete-orphan')
    #eleve    = db.relationship('Eleve',   backref=db.backref('scolarites', lazy=True))
    #classe   = db.relationship('Classe',  backref=db.backref('scolarites', lazy=True))
    #paiements = db.relationship('Paiement', backref='scolarite', lazy=True,
                                 #cascade='all, delete-orphan')
                                 

    @property
    def montant_paye(self):
        return sum(p.montant for p in self.paiements)

    @property
    def montant_restant(self):
        return max(0.0, self.montant_total - self.montant_paye)

    @property
    def est_solde(self):
        return self.montant_restant <= 0

    @property
    def pourcentage_paye(self):
        if self.montant_total == 0:
            return 100
        return min(100, int(self.montant_paye / self.montant_total * 100))

    def __repr__(self):
        return f'<Scolarite eleve={self.eleve_id} total={self.montant_total}>'


class Paiement(db.Model):
    """Un versement effectué pour une scolarité"""
    __tablename__ = 'paiement'

    id             = db.Column(db.Integer, primary_key=True)
    scolarite_id   = db.Column(db.Integer, db.ForeignKey('scolarite.id'), nullable=False)
    montant        = db.Column(db.Float, nullable=False)
    date_paiement  = db.Column(db.DateTime, default=datetime.utcnow)
    numero_recu    = db.Column(db.String(50), unique=True, nullable=False)
    mode_paiement  = db.Column(db.String(30), default='espèces')   # espèces, mobile money, virement
    notes          = db.Column(db.String(200), nullable=True)
    encaisseur     = db.Column(db.String(100), nullable=True)       # nom du caissier

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.numero_recu:
            self.numero_recu = self._generer_numero()

    @staticmethod
    def _generer_numero():
        """Génère un numéro de reçu unique : REC-YYYYMMDD-XXXX"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        uid = uuid.uuid4().hex[:6].upper()
        return f'REC-{date_str}-{uid}'

    def __repr__(self):
        return f'<Paiement {self.numero_recu} {self.montant}>'


# terminer 


class MatriculeUsed(db.Model):
    """Historique des matricules par école — jamais réattribués au sein d'un même établissement."""
    __tablename__ = 'matricule_used'
    __table_args__ = (
        db.UniqueConstraint('matricule', 'ecole_id', name='uq_matricule_ecole'),
    )

    id        = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), nullable=False)
    ecole_id  = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False)
    used_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Note(db.Model):
    __tablename__ = 'note'

    id         = db.Column(db.Integer, primary_key=True)
    eleve_id   = db.Column(db.Integer, db.ForeignKey('eleve.id'),   nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=False)
    note       = db.Column(db.Float, nullable=False)
    trimestre  = db.Column(db.String(2), nullable=False)
    statut     = db.Column(db.String(10), default='active')
    date_saisie = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Note {self.note} - Élève:{self.eleve_id} Matière:{self.matiere_id}>'


# ============================================================
# 1. À AJOUTER dans models.py
# ============================================================
 
class Config(db.Model):
    """Table clé-valeur pour les paramètres globaux de l'application."""
    __tablename__ = 'config'
 
    id    = db.Column(db.Integer, primary_key=True)
    cle   = db.Column(db.String(100), unique=True, nullable=False)   # ex: 'whatsapp_number'
    valeur = db.Column(db.String(255), nullable=True)
 
    @staticmethod
    def get(cle, default=None):
        row = Config.query.filter_by(cle=cle).first()
        return row.valeur if row else default
 
    @staticmethod
    def set(cle, valeur):
        row = Config.query.filter_by(cle=cle).first()
        if row:
            row.valeur = valeur
        else:
            row = Config(cle=cle, valeur=valeur)
            db.session.add(row)
        db.session.commit()