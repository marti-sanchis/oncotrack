from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Enum, Boolean, Date, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
#import pandas as pd

# Initialize Flask SQLAlchemy
db = SQLAlchemy()

# Association Tables
patient_has_variant = db.Table(
    'patient_has_variant',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id')),
    db.Column('variant_id', db.Integer, db.ForeignKey('variant.variant_id'))
)

patient_treated_with_drug = db.Table(
    'patient_treated_with_drug',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id')),
    db.Column('drug_id', db.Integer, db.ForeignKey('drug.drug_id'))
)

personnel_attend_to_patient = db.Table(
    'personnel_attend_to_patient',
    db.Column('patient_id', db.Integer, db.ForeignKey('patient.patient_id')),
    db.Column('personnel_id', db.Integer, db.ForeignKey('healthcare_personnel.personnel_id'))
)

# Models
class CancerType(db.Model):
    __tablename__ = 'cancer_type'
    cancer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cancer_type = db.Column(db.String(50), nullable=False)

class Patient(db.Model):
    __tablename__ = 'patient'
    patient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    DNI = db.Column(db.String(20))
    gender = db.Column(db.Enum('M', 'F', 'Other'))
    age = db.Column(db.Integer)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    cancer_id = db.Column(db.Integer, db.ForeignKey('cancer_type.cancer_id'))
    cancer = db.relationship("CancerType")

class VCFEntry(db.Model):
    __tablename__ = 'vcf_entry'
    vcf_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'))
    path = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.Date)
    processed = db.Column(db.Boolean)
    delete_date = db.Column(db.Date, nullable=True)

class Gene(db.Model):
    __tablename__ = 'gene'
    gene_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gene_symbol = db.Column(db.String(50))
    gene_name = db.Column(db.String(50))
    location = db.Column(db.String(50))
    role_in_cancer = db.Column(db.String(50))

class Variant(db.Model):
    __tablename__ = 'variant'
    variant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variant_type = db.Column(db.String(50))
    change_id = db.Column(db.String(100))
    gene_id = db.Column(db.Integer, db.ForeignKey('gene.gene_id'))
    gene = db.relationship("Gene")

class Drug(db.Model):
    __tablename__ = 'drug'
    drug_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))

class DrugAssociation(db.Model):
    __tablename__ = 'drug_association'
    association_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gene_id = db.Column(db.Integer, db.ForeignKey('gene.gene_id'))
    variant_id = db.Column(db.Integer, db.ForeignKey('variant.variant_id'))
    drug_id = db.Column(db.Integer, db.ForeignKey('drug.drug_id'))
    cancer_id = db.Column(db.Integer, db.ForeignKey('cancer_type.cancer_id'))
    response = db.Column(db.Enum('resistance', 'treatment'))
    source = db.Column(db.Enum('Source1', 'Source2', 'Source3'))
    reference = db.Column(db.Text)



class HealthcarePersonnel(db.Model):
    __tablename__ = 'healthcare_personnel'
    personnel_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    role_name = db.Column(db.String(50), nullable=False)




from app import db
from models import Gene, Variant, Drug, DrugAssociation, CancerType

# Function to load data from CSV into the database
def load_data_from_csv():
    # Load CSVs into DataFrames
    gene_df = pd.read_csv('path/to/gene.csv')
    variant_df = pd.read_csv('path/to/variant.csv')
    drug_df = pd.read_csv('path/to/drug.csv')
    drug_association_df = pd.read_csv('path/to/drug_association.csv')
    cancer_type_df = pd.read_csv('path/to/cancer_type.csv')

    # Insert data into CancerType table
    for _, row in cancer_type_df.iterrows():
        cancer_type = CancerType(cancer_type=row['cancer_type'])
        db.session.add(cancer_type)
    db.session.commit()  # Commit after inserting cancer types

    # Insert data into Gene table
    for _, row in gene_df.iterrows():
        gene = Gene(
            gene_symbol=row['gene_symbol'],
            gene_name=row['gene_name'],
            location=row['location'],
            role_in_cancer=row['role_in_cancer']
        )
        db.session.add(gene)
    db.session.commit()  # Commit after inserting genes

    # Insert data into Variant table
    for _, row in variant_df.iterrows():
        variant = Variant(
            variant_type=row['variant_type'],
            change_id=row['change_id'],
            gene_id=row['gene_id']  # Assumes gene_id in CSV corresponds to a valid gene_id
        )
        db.session.add(variant)
    db.session.commit()  # Commit after inserting variants

    # Insert data into Drug table
    for _, row in drug_df.iterrows():
        drug = Drug(name=row['name'])
        db.session.add(drug)
    db.session.commit()  # Commit after inserting drugs

    # Insert data into DrugAssociation table
    for _, row in drug_association_df.iterrows():
        drug_association = DrugAssociation(
            gene_id=row['gene_id'],
            variant_id=row['variant_id'],
            drug_id=row['drug_id'],
            cancer_id=row['cancer_id'],
            response=row['response'],
            source=row['source'],
            reference=row['reference']
        )
        db.session.add(drug_association)
    db.session.commit()  # Commit after inserting drug associations

    print("Data successfully loaded from CSV files!")

# Call the function to load data
load_data_from_csv()

