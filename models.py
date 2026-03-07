from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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

    notes = db.relationship('Note', backref='eleve', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Eleve {self.matricule} - {self.prenom} {self.nom}>'


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
