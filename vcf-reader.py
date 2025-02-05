import pysam
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import mysql.connector
import pysam
import pandas as pd

# Start connection with local DB
db_connection = mysql.connector.connect(
    host="localhost",       
    user="root",
    password="1234", 
    database="variantes_prueba"  
)
cursor = db_connection.cursor()

# Read variant file (Variant Call Format) with pysam function.
vcf = pysam.VariantFile("/home/marti/MBHS/DBW/OncoTrack/vcf_mutations/GBM_sample_muts.hg38.vcf")
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
for variant in variants:
    chrom = variant["chrom"]
    pos = variant["pos"]
    ref = variant["ref"]
    alt = variant["alt"]
        
    query = """
        SELECT GENOMIC_MUTATION_ID, MUTATION_DESCRIPTION, GENE_SYMBOL
        FROM cosmic_mutations
        WHERE CHROMOSOME = %s
        AND GENOME_START = %s
        AND GENOMIC_WT_ALLELE = %s
        AND GENOMIC_MUT_ALLELE = %s
    """
    cursor.execute(query, (chrom, pos, ref, alt))
    matching_rows = cursor.fetchall()

    for row in matching_rows:
        matched_variants.append({
            "gene_sym":row[2],
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "cosmic_id": row[0],
            "mutation_desc": row[1]
        })

for variant in matched_variants:
    print(variant)

cursor.close()
db_connection.close()