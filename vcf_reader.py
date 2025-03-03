import pysam
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config

def process_vcf(vcf_file_path, patient_id=1):

    if not os.path.exists(vcf_file_path):
        #print(f"VCF file {vcf_file_path} not found, skipping processing.")
        return  # Exit if no file is found

    # Engine with the URI to the database
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
    # Create session to interact with database
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if the patient exists in the database
    existing_patient = session.execute(
        text("SELECT 1 FROM patient WHERE patient_id = :patient_id"),
        {"patient_id": patient_id}
    ).fetchone()

    if not existing_patient:
        print(f"Error: Patient ID {patient_id} does not exist in the patient table.")
        session.close()  # Close the session to avoid resource leakage
        return  # Exit if the patient does not exist

    # Read variant file (Variant Call Format) with pysam function.
    # vcf_file_path = "files/AML_sample_muts.hg38.vcf"
    vcf = pysam.VariantFile(vcf_file_path)
    variants = []

    # List of dictionaries: chromosome, position, reference and alternative alleles (considering multiple alt alleles). 
    for record in vcf:
        chrom = record.chrom 
        pos = record.pos  
        ref = record.ref  
        for alt in record.alts:
            variants.append({
                "chrom": chrom,
                "pos": pos,
                "ref": ref,
                "alt": alt  
            })

    # Search for matching variants in local DB.
    query = text("""
        SELECT variant_id FROM variant
        WHERE chromosome = :chrom
        AND position = :pos
        AND reference = :ref
        AND alternative = :alt
    """)

    matched_variants = []
    for variant in variants:
        result = session.execute(query, variant).fetchone()
        if result:
            matched_variants.append(result[0])

    if matched_variants:
        insert_query = text("""
            INSERT INTO patient_has_variant (patient_id, variant_id)
            SELECT :patient_id, :variant_id
            WHERE NOT EXISTS (
                SELECT 1 FROM patient_has_variant 
                WHERE patient_id = :patient_id AND variant_id = :variant_id
            )
        """)
        for variant_id in matched_variants:
            session.execute(insert_query, {"patient_id": patient_id, "variant_id": variant_id})
        
        session.commit()
        session.close()

process_vcf("uploads/AML_sample_muts.hg38.vcf")