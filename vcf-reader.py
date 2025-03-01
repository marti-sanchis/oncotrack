import pysam
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app import app
from models_proba import db
from config import Config

# Engine with the URI to the database
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
# Create session to interact with database
Session = sessionmaker(bind=engine)
session = Session()

# Read variant file (Variant Call Format) with pysam function.
vcf_file_path = "files/AML_sample_muts.hg38.vcf"
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
query = text("""
    SELECT v.variant_id, v.variant_type, v.gene_id, g.gene_name
    FROM variant v
    LEFT JOIN gene g ON v.gene_id = g.gene_id
    WHERE v.chromosome = :chrom
    AND v.position = :pos
    AND v.reference = :ref
    AND v.alternative = :alt
""")

matched_variants = []
for variant in variants:
    result = session.execute(query, variant).fetchall()
    for row in result:
        matched_variants.append({
            "variant_id": row[0],
            "variant_type": row[1],
            "gene_id": row[2] if len(row) > 2 else None,
            "chromosome": variant["chrom"],
            "position": variant["pos"],
            "reference": variant["ref"],
            "alternative": variant["alt"]
        })

# Print results
# for variant in matched_variants:
#     print(variant)

for variant in matched_variants:
    gene_query = text("""
        SELECT gene_name, gene_symbol FROM gene WHERE gene_id = :gene_id
    """)
    gene_result = session.execute(gene_query, {"gene_id": variant["gene_id"]}).fetchone()
    
    if gene_result:
        variant["gene_name"] = gene_result[0] if gene_result[0] else "Unknown"
        variant["gene_symbol"] = gene_result[1] if gene_result[1] else "Unknown"
    else:
        variant["gene_name"] = "Unknown"
        variant["gene_symbol"] = "Unknown"

# Print results mostrando variant_id, variant_type, gene_symbol y gene_name
for variant in matched_variants:
    print({
        "variant_id": variant["variant_id"],
        "variant_type": variant["variant_type"],
        "gene_symbol": variant["gene_symbol"],
        "gene_name": variant["gene_name"]
    })

# Close session
session.close()