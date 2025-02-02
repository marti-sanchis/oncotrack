import pysam
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from model import db, Patient, Variant, Gene, patient_has_variant

# Configurar la conexión a la base de datos
DATABASE_URI = ""  # Cambiar por la URI real de la base de datos
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

def parse_vcf(vcf_file):
    """Parsea un archivo VCF y extrae la información relevante."""
    vcf = pysam.VariantFile(vcf_file)
    variants = []
    
    for record in vcf:
        chrom = record.chrom
        pos = record.pos
        ref = record.ref
        alt = ','.join(str(a) for a in record.alts)
        cosmic_ids = [entry.split('=')[1] for entry in record.info if entry.startswith('COSMIC')]  # Extraer ID de Cosmic si está anotado
        
        variants.append({
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "cosmic_ids": cosmic_ids
        })
    
    return variants

