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
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    nurse_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    nurse = db.relationship('User', foreign_keys=[nurse_id])
    variants = db.relationship('Variant', secondary=patient_has_variant, backref=db.backref('patients', lazy=True))
    
    def __repr__(self):
        return f"Patient('{self.name}', '{self.doctor_id}')"

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
<<<<<<< HEAD
    gene_id = db.Column(db.String(20), db.ForeignKey('gene.gene_id'))
=======
    gene_id = db.Column(db.String(10), db.ForeignKey('gene.gene_id'))
>>>>>>> 5bfd13362efb700523aa1b097e7b4c55794d90db

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
<<<<<<< HEAD
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
    association = db.Column(db.Enum('resistance', 'treatment','generic'))
    reference = db.Column(db.String(20))
=======
    gene_name = db.Column(db.String(50))
    location = db.Column(db.String(50),nulleable=False)
    role_in_cancer = db.Column(db.String(50), nulleable=False)

class Drug(db.Model):
    __tablename__ = 'drug'
    drug_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(100))

class DrugAssociation(db.Model):
    __tablename__ = 'drug_association'
    variant_id = db.Column(db.String, db.ForeignKey('variant.variant_id'), nulleable=True)
    gene_id=db.Column(db.String, db.ForeignKey('gene.gene_id'), nulleable=True)
    drug_id = db.Column(db.String, db.ForeignKey('drug.drug_id'))
    cancer_id = db.Column(db.Integer, db.ForeignKey('cancer_type.cancer_id'))
    response = db.Column(db.Enum('resistance', 'treatment'))
    source = db.Column(db.Enum('Source1', 'Source2', 'Source3'))
    reference = db.Column(db.Text)

class CancerType(db.Model):
    __tablename__ = 'cancer_type'
    cancer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cancer_type = db.Column(db.String(50), nullable=False)


>>>>>>> 5bfd13362efb700523aa1b097e7b4c55794d90db
