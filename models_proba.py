from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

patient_has_variant = db.Table(
    'patient_has_variant',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.id')),
    db.Column('variant_id', db.String(20), db.ForeignKey('variant.variant_id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.role}')"

    # Password hash handling
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Se tendra que cambiar a False
    nurse_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    nurse = db.relationship('User', foreign_keys=[nurse_id])

    variants = db.relationship('Variant', secondary=patient_has_variant, backref=db.backref('patients', lazy=True))
    
    def __repr__(self):
        return f"Patient('{self.name}', '{self.doctor_id}')"

class Variant(db.Model):
    __tablename__ = 'variant'
    variant_id = db.Column(db.String(20), primary_key=True)
    chromosome = db.Column(db.String(10))
    position = db.Column(db.BigInteger)
    reference = db.Column(db.String(100))
    alternative = db.Column(db.String(100))
    variant_type = db.Column(db.Text())
    gene = db.Column(db.String(50))

    __table_args__ = (
        Index('idx_chr', 'chromosome'),
        Index('idx_pos', 'position'),
        Index('idx_ref', 'reference'),
        Index('idx_alt', 'alternative')
        )

