from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_proba import db, Variant, Gene, Drug, CancerType, DrugAssociation, MutationalSignature
from config import Config
import pandas as pd
import numpy as np

def load_data(file_path, model, column_map):
    df = pd.read_csv(file_path, sep='\t')
    df = df.replace({np.nan: None})
    
    try:
        objects = []
        for _, row in df.iterrows():
            obj_data = {attr: row[col] for col, attr in column_map.items()}
            objects.append(model(**obj_data))
        
        session.bulk_save_objects(objects)
        session.commit()
        print(f'Table "{model.__tablename__}" successfully load with {len(objects)} rows.')
    
    except Exception as e:
        session.rollback()
        print(f"Error {model.__tablename__}: {e}")


# Engine with the URI to the database
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
# Create session to interact with database
Session = sessionmaker(bind=engine)
session = Session()

# Create all tables
db.metadata.create_all(engine)  
print("All tables correctly created.")

# Load cosmic gene table
load_data("tables/genes.tsv", Gene, {
    "gene_id": "gene_id",
    "gene_symbol": "gene_symbol",
    "gene_name": "gene_name",
    "location": "location",
    "role_in_cancer": "role_in_cancer"
})

# Load drugs table
load_data("tables/drug.tsv", Drug, {
    "drug_id": "drug_id",
    "name": "name"
})

# Load cancer types table
load_data("tables/cancer_type.tsv", CancerType, {
    "cancer_type": "cancer_type"
})

# Load cosmic mutational signatures
load_data("tables/mutsignatures.tsv", MutationalSignature, {
    "signature_id": "signature_id",
    "description":"description",
    "aetiology":"aetiology",
    "comments":"comments",
    "link":"link"
})

# Load comsic mutation file
df = pd.read_csv('tables/variants.tsv', sep='\t')
df = df.where(pd.notna(df), "")

try:
    # Set batch size
    BATCH_SIZE = 100000
    variants = []
    for _, row in df.iterrows():
        variants.append(Variant(
            variant_id=row['variant_id'],
            chromosome=row['chromosome'],
            position=row['position'],
            reference=row['reference'],
            alternative=row['alternative'],
            aa_mutation=row['aa_mutation'],
            variant_type=row['variant_type'],
            gene_id=row['gene_id']

        ))
    # Insert by batch
        if len(variants) >= BATCH_SIZE:
            session.bulk_save_objects(variants)
            session.commit()
            variants = []
            print(f"Batch of {BATCH_SIZE} rows successfully loaded.")

    # Insert last batch
    if variants:
        session.bulk_save_objects(variants)
        session.commit()
    print("Table \"variants\" successfully loaded")
except Exception as e:
    print(e)

# Load drug association table
load_data("tables/drug_association.tsv", DrugAssociation, {
    "drug_id": "drug_id",
    "gene_id": "gene_id",
    "variant_id": "variant_id",
    "association": "association",
    "cancer_id": "cancer_id",
    "subtype":"subtype",
    "reference": "reference"
})

session.close()
