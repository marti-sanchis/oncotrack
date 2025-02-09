import pysam
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app import app
from models_proba import db
from config import Config

# Use connection defined in Flask
engine = db.engine  
Session = sessionmaker(bind=engine)
session = Session()


# Read variant file (Variant Call Format) with pysam function.
vcf_file_path = "/home/marti/MBHS/DBW/OncoTrack/vcf_mutations/GBM_sample_muts.hg38.vcf"
vcf = pysam.VariantFile(vcf_file_path)
variants = []

# List of dictionaries: chromosome, position, reference and alternative alleles (considering multiple alt alleles). 
for record in vcf:
    chrom = record.chrom 
    pos = record.pos  
    ref = record.ref  
    
    for alt in record.alts:
        if len(ref) > 1 or len(alt) > 1:
            ref = ref[1:] if len(ref) > 1 else ""
            alt = alt[1:] if len(alt) > 1 else ""
        variants.append({
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt  
        })

# Search for matching variants in local DB.
matched_variants = []
query = """
    SELECT GENOMIC_MUTATION_ID, MUTATION_DESCRIPTION, GENE_SYMBOL
    FROM cosmic_mutations
    WHERE CHROMOSOME = %s
    AND GENOME_START = %s
    AND GENOMIC_WT_ALLELE = %s
    AND GENOMIC_MUT_ALLELE = %s
"""

for variant in variants:
    result = session.execute(query, variant).fetchall()
    for row in result:
        matched_variants.append({
            "gene_sym": row[2],
            "chrom": variant["chrom"],
            "pos": variant["pos"],
            "ref": variant["ref"],
            "alt": variant["alt"],
            "cosmic_id": row[0],
            "mutation_desc": row[1]
        })

# ✅ Mostrar resultados
for variant in matched_variants:
    print(variant)

# ✅ Cerrar sesión
session.close()