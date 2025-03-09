import pysam
import shutil
import os
import gseapy as gp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from SigProfilerAssignment import Analyzer as Analyze
import sigProfilerPlotting as sigPlt
import re
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pdf2image import convert_from_path

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

    # Direcotories for the analysis output
    outdir = f"analysis_results/Patient_{patient_id}"
    enrichr_dir = os.path.join(outdir, "enrichment")
    sigprofiler_dir = os.path.join(outdir, "sigProfiler")

    # Create directories
    os.makedirs(enrichr_dir, exist_ok=True)
    os.makedirs(sigprofiler_dir, exist_ok=True)

    # Copy VCF to sigProfiler path
    vcf_filename = os.path.basename(vcf_file_path)
    copied_vcf_path = os.path.join(sigprofiler_dir, vcf_filename)
    shutil.copy(vcf_file_path, copied_vcf_path)

    # Enrichment analysis
    if gene_set:
        gene_list=list(gene_set)
        gp.enrichr(gene_list=gene_list, gene_sets="KEGG_2021_Human", organism="human", outdir=enrichr_dir)

    # Mutational signatures
    Analyze.cosmic_fit(f"{sigprofiler_dir}", 
                       f"{sigprofiler_dir}", 
                       input_type="vcf", 
                       cosmic_version=3, 
                       genome_build="GRCh38", 
                       export_probabilities_per_mutation=False)
    if os.path.exists(copied_vcf_path):
        os.remove(copied_vcf_path)

    sig_decomp_path = os.path.join(sigprofiler_dir, "Assignment_Solution/Solution_Stats/Assignment_Solution_Signature_Assignment_log.txt")
    cosine_sim_path = os.path.join(sigprofiler_dir, "Assignment_Solution/Solution_Stats/Assignment_Solution_Samples_Stats.txt")

    with open(sig_decomp_path, 'r') as file:
        content = file.read()

    # Patrón para buscar la sección "Composition After Add-Remove" y extraer las firmas
    pattern = r"Composition After Add-Remove[\s\S]*?([\w\s]+)\n([\d\.]+(?:\s+[\d\.]+)*)"
    match = re.search(pattern, content)
    
    if match:
        # Get signatures and values
        signatures_line = match.group(2)
        signature_names = match.group(1).split()
        signature_values = re.findall(r'(\d+\.\d+|\d+)', signatures_line)[1:]
        
        # Associate signatures with percentage
        signatures = {signature_names[i]: float(signature_values[i]) for i in range(len(signature_names))}
        total = sum(signatures.values())
        percentages = {signature: (count / total) * 100 for signature, count in signatures.items()}
    else:
        print("No se encontró la composición después de Add-Remove en el archivo.")
        return None
        
    labels = list(percentages.keys())
    sizes = list(percentages.values())
    plt.rcParams["font.family"] = "Liberation Sans"

    # Color palette "Set2"
    colormap = cm.get_cmap("Set2", len(labels))
    colors = [colormap(i) for i in range(len(labels))]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(8, 8))

    # Donut plot
    wedges, label_texts, percent_texts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%', startangle=140,
        colors=colors, wedgeprops={'edgecolor': 'white'}, pctdistance=0.75,
    )
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    ax.add_artist(centre_circle)

    for lbl in label_texts:
        lbl.set_fontsize(16)
        lbl.set_color('black')
        lbl.set_fontweight('bold') 
    for pct in percent_texts:
        pct.set_fontsize(16)
        pct.set_color('black')
        pct.set_fontweight('bold')  

    ax.set_title("Decomposed Mutational Signature", fontsize=20, fontweight='bold')

    with open(cosine_sim_path, 'r') as file:
        lines = file.readlines()

    # Get Cosine Similarity
    cosine_similarity = None
    if len(lines) > 1:
        second_line = lines[1].split("\t")
        cosine_similarity = second_line[2]  

    if cosine_similarity:
        ax.text(
            0.2, -0.05, f"Cosine Similarity: {cosine_similarity}", 
            ha='center', va='center', fontsize=18, fontweight='bold', transform=ax.transAxes
        )
    else:
        ax.text(
            0.2, -0.05, "Cosine Similarity: N/A", 
            ha='center', va='center', fontsize=18, fontweight='bold', transform=ax.transAxes
        )
    # Save plot
    plt.tight_layout()
    plt.savefig(f"{sigprofiler_dir}/signature_pie_chart.png", dpi=300)

    # Get SBS96 plot
    SBS96_path=os.path.join(sigprofiler_dir,"output/SBS/Input_vcffiles.SBS96.all")
    sigPlt.plotSBS(SBS96_path, sigprofiler_dir, f"Patient_{patient_id}", "96", percentage=False)
    pdf_path=os.path.join(sigprofiler_dir, f"SBS_96_plots_Patient_{patient_id}.pdf")
    output_png =os.path.join(sigprofiler_dir,f"SBS96_plot.png")
    images = convert_from_path(pdf_path, dpi=300)
    images[0].save(output_png, "PNG")

# process_vcf("/home/marti/MBHS/DBW/OncoTrack/oncotrack/uploads/HNSC_sample_muts.hg38.vcf",2)
