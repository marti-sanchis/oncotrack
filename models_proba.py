from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

patient_has_variant = db.Table(
    'patient_has_variant',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id', ondelete="CASCADE")),
    db.Column('variant_id', db.String(20), db.ForeignKey('variant.variant_id'))
)
patient_has_drug = db.Table(
    'patient_has_drug',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id', ondelete="CASCADE")),
    db.Column('drug_id', db.String(20), db.ForeignKey('drug.drug_id'))
)
patient_has_signature = db.Table('patient_has_signature',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id'), primary_key=True),
    db.Column('signature_id', db.String(50), db.ForeignKey('mutational_signature.signature_id'), primary_key=True))

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
    patient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    DNI = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.Enum('M', 'F', 'Other'))
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    cancer_id = db.Column(db.Integer, db.ForeignKey('cancer_type'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    nurse_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default="queued")
    
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    nurse = db.relationship('User', foreign_keys=[nurse_id])
    variants = db.relationship('Variant', secondary=patient_has_variant, backref=db.backref('patients', lazy=True), cascade="all, delete")
    drugs = db.relationship('Drug', secondary=patient_has_drug, backref=db.backref('patients', lazy=True), cascade="all, delete")
    signatures = db.relationship('MutationalSignature', secondary=patient_has_signature, backref=db.backref('patients', lazy=True), cascade="all, delete")    
    
    def __repr__(self):
        return f"Patient('{self.name}', '{self.doctor_id}')"
    
class MutationalSignature(db.Model):
    signature_id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    aetiology = db.Column(db.Text, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"MutationalSignature('{self.name}')"
    
class Drug(db.Model):
    __tablename__ = 'drug'
    drug_id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))

class CancerType(db.Model):
    __tablename__ = 'cancer_type'
    cancer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cancer_type = db.Column(db.String(50), nullable=False)

class Variant(db.Model):
    __tablename__ = 'variant'
    variant_id = db.Column(db.String(20), primary_key=True)
    chromosome = db.Column(db.String(10))
    position = db.Column(db.BigInteger)
    reference = db.Column(db.String(400))
    alternative = db.Column(db.String(400))
    aa_mutation = db.Column(db.String(15))
    variant_type = db.Column(db.String(200))
    gene_id = db.Column(db.String(20), db.ForeignKey('gene.gene_id'))


    __table_args__ = (
        Index('idx_chr', 'chromosome'),
        Index('idx_pos', 'position'),
        Index('idx_ref', 'reference'),
        Index('idx_alt', 'alternative')
        )

class Gene(db.Model):
    __tablename__ = 'gene'
    gene_id = db.Column(db.String(20), primary_key=True)
    gene_symbol = db.Column(db.String(50))
    gene_name = db.Column(db.String(100))
    location = db.Column(db.String(50))
    role_in_cancer = db.Column(db.String(50), nullable=True)

class DrugAssociation(db.Model):
    __tablename__ = 'drug_association'
    association_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gene_id = db.Column(db.String(20), db.ForeignKey('gene.gene_id'))
    variant_id = db.Column(db.String(20), db.ForeignKey('variant.variant_id'))
    drug_id = db.Column(db.String(20), db.ForeignKey('drug.drug_id'))
    cancer_id = db.Column(db.Integer, db.ForeignKey('cancer_type.cancer_id'))
    subtype=db.Column(db.String(200))
    association = db.Column(db.Enum('resistance', 'specific','generic'))
    reference = db.Column(db.String(20))
