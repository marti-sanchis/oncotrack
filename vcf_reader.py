import pysam
import os
import gseapy as gp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from SigProfilerAssignment import Analyzer as Analyze


def process_vcf(vcf_file_path, patient_id):

    if not os.path.exists(vcf_file_path):
        print(f"VCF file {vcf_file_path} not found, skipping processing.")
        return  # Exit if no file is found

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Verificar que el patient_id es válido
    existing_patient = session.execute(
        text("SELECT 1 FROM patient WHERE patient_id = :patient_id"),
        {"patient_id": patient_id}
    ).fetchone()

    if not existing_patient:
        print(f"Error: Patient ID {patient_id} does not exist in the patient table.")
        session.close()
        return  

    vcf = pysam.VariantFile(vcf_file_path)
    variants = []

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
        print(f"Ejecutando inserción en patient_has_variant")
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

    gene_query = text("""
        SELECT DISTINCT g.gene_symbol 
        FROM gene g
        JOIN variant v ON g.gene_id = v.gene_id
        WHERE v.variant_id = :variant_id
    """)
    
    print("starting gene name query")
    gene_set = set()
    for variant_id in matched_variants:
        gene_result = session.execute(gene_query, {"variant_id": variant_id}).fetchall()
        for row in gene_result:
            gene_set.add(row[0])
    print(gene_set)
    
    session.close()

    # Enrichment analysis
    if gene_set:
        outdir = f"enrichr_results/Patient_{patient_id}"
        gene_list=list(gene_set)
        gp.enrichr(gene_list=gene_list, gene_sets="KEGG_2021_Human", organism="human", outdir=outdir)

    # Mutational signatures
    # Analyze.cosmic_fit("/home/marti/MBHS/DBW/OncoTrack/oncotrack/files/prova", 
    #                    "/home/marti/MBHS/DBW/OncoTrack/oncotrack/files/results_assignment", 
    #                    input_type="vcf", 
    #                    cosmic_version=3.4, 
    #                    genome_build="GRCh38", 
    #                    export_probabilities_per_mutation=False)
