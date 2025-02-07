import pymysql
from app import app
from models_proba import db, Variant
from config import Config
import pandas as pd
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker


# Conect to MySQL to create the database if it doesn't exist.
connection = pymysql.connect(
    host=Config.MYSQL_HOST,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD
)

with connection.cursor() as cursor:
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB}")
    print(f"Database '{Config.MYSQL_DB}' verified or created.")

connection.close()

# Initialise all tables inside the recently created database.
BATCH_SIZE = 100000 
with app.app_context():
    try:
        # Verificar si las tablas existen
        inspector = inspect(db.engine)
        if not inspector.has_table('variant'):  # Verifica si la tabla 'variant' existe
            # Si la tabla no existe, entonces creamos las tablas
            db.create_all()
            print("Tablas creadas correctamente.")
            # Cargar y procesar el archivo
            df = pd.read_csv('/home/marti/MBHS/DBW/OncoTrack/cosmut_db.tsv', sep='\t')
            df = df.where(pd.notna(df), "")  # Reemplazar valores NaN con cadenas vacías

            # Renombrar columnas
            df.rename(columns={
                'GENOMIC_MUTATION_ID': 'variant_id',
                'CHROMOSOME': 'chromosome',
                'GENOME_START': 'position',
                'GENOMIC_WT_ALLELE': 'reference',
                'GENOMIC_MUT_ALLELE': 'alternative',
                'MUTATION_DESCRIPTION': 'variant_type',
                'GENE_SYMBOL': 'gene'
            }, inplace=True)

            # Conectar a la base de datos y preparar la sesión
            engine = db.engine
            Session = sessionmaker(bind=engine)
            session = Session()

            # Insertar por lotes
            variants = []
            for _, row in df.iterrows():
                variants.append(Variant(
                    variant_id=row['variant_id'],
                    chromosome=row['chromosome'],
                    position=row['position'],
                    reference=row['reference'],
                    alternative=row['alternative'],
                    variant_type=row['variant_type'],
                    gene=row['gene']
                ))

                # Hacer commit cada vez que el batch sea completo
                if len(variants) % BATCH_SIZE == 0:
                    session.bulk_save_objects(variants)
                    session.commit()
                    variants = []
                    print(f"Batch de {BATCH_SIZE} filas insertado correctamente")

            # Insertar lo que quede en el último lote
            if variants:
                session.bulk_save_objects(variants)
                session.commit()
            print("Datos insertados correctamente")
        else:
            print("Las tablas ya existen. No es necesario crear nuevamente.")

    except Exception as e:
        print(f"Error al insertar datos: {e}")
        session.rollback()
