from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_proba import db, Variant
from config import Config
import pandas as pd

# Overwritte engine with the URI to the database
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)

# Create session to interact with database
Session = sessionmaker(bind=engine)
session = Session()
# Create all tables
db.metadata.create_all(engine)  
print("All tables correctly created.")

# Load comsic mutation file
df = pd.read_csv('/home/marti/MBHS/DBW/OncoTrack/variants.tsv', sep='\t')
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
            gene=row['gene']
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



session.close()
