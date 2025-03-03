import os
import pandas as pd
from Bio import PDB
import mdtraj as md

# Lista de aminoácidos estándar en PDB

def extract_aa_composition(pdb_file):
    """Extrae la composición de aminoácidos del pocket PDB."""

    aa_comp_list = []
    with open(pdb_path, "r") as fd:
        for line in fd:
            line = line.strip("\n")
            if line.startswith("ATOM"):
                chain = line[21]
                residue = f"{line[17:20]} {chain} {line[22:26].strip()}"
                aa_comp_list.append(line[17:20])

    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure("pocket", pdb_file)
    aa_counts = {aa: 0 for aa in aa_comp_list}

    for model in structure:
        for chain in model:
            for residue in chain:
                if residue.get_resname() in AMINO_ACIDS:
                    aa_counts[residue.get_resname()] += 1

    total = sum(aa_counts.values())
    if total > 0:
        return {aa: count / total for aa, count in aa_counts.items()}  # Normalización
    else:
        return aa_counts

# Ejemplo de uso
pdb_path = input("")
features = extract_aa_composition(pdb_path)
print("AA composition:", features)  # {'ALA': 0.1, 'ARG': 0.05, ...}

# Propiedades fisicoquímicas promedio de los AA (Ejemplo)
HYDROPHOBICITY = {"ALA": 1.8, "ARG": -4.5, "ASN": -3.5, "ASP": -3.5, "CYS": 2.5, 
                  "GLN": -3.5, "GLU": -3.5, "GLY": -0.4, "HIS": -3.2, "ILE": 4.5,
                  "LEU": 3.8, "LYS": -3.9, "MET": 1.9, "PHE": 2.8, "PRO": -1.6,
                  "SER": -0.8, "THR": -0.7, "TRP": -0.9, "TYR": -1.3, "VAL": 4.2}

def compute_pocket_hydrophobicity(aa_composition):
    """Calcula la hidrofobicidad promedio del pocket."""
    return sum(aa_composition[aa] * HYDROPHOBICITY[aa] for aa in aa_composition)

pocket_hydro = compute_pocket_hydrophobicity(features)
print("\n","Hidrofobicidad:", pocket_hydro)

def compute_pocket_volume(pdb_file):
    """Calcula el volumen del pocket usando MDTraj."""
    traj = md.load(pdb_file)
    xyz = traj.xyz[0]  # Coordenadas atómicas
    min_coords = xyz.min(axis=0)
    max_coords = xyz.max(axis=0)
    volume = ((max_coords - min_coords).prod())  # Aproximación cúbica
    return volume

pocket_volume = compute_pocket_volume(pdb_path)
print("\n","Volumen del pocket:", pocket_volume)

CHARGES = {"ARG": +1, "LYS": +1, "ASP": -1, "GLU": -1, "HIS": 0.5}

def compute_pocket_charge(aa_composition):
    """Calcula la carga neta del pocket."""
    return sum(aa_composition[aa] * CHARGES.get(aa, 0) for aa in aa_composition)

pocket_charge = compute_pocket_charge(features)
print("\n", "Carga neta:", pocket_charge)

def extract_features(pdb_file):
    """Extrae todas las características de un pocket PDB."""
    aa_composition = extract_aa_composition(pdb_file)
    pocket_charge = compute_pocket_charge(aa_composition)
    hydrophobicity = compute_pocket_hydrophobicity(aa_composition)
    volume = compute_pocket_volume(pdb_file)

    features = {"hydrophobicity": hydrophobicity, "pocket_charge": pocket_charge, "volume": volume, **aa_composition}
    return features




# Extraer features de múltiples archivos
pocket_files = ["pocket1.pdb", "pocket2.pdb", "pocket3.pdb"]
#df = pd.DataFrame([extract_features(pdb) for pdb in pocket_files])
df = pd.DataFrame([extract_features(pdb_path)])

print(df.head())
'''
##### RANDOM FOREST #####

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Supongamos que tenemos etiquetas para cada pocket
labels = ["Pocket_A", "Pocket_B", "Pocket_C"]  # Reemplaza con tus clases
df["label"] = labels

# Dividir datos en entrenamiento y prueba
X = df.drop(columns=["label"])
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Entrenar Random Forest
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# Evaluación
y_pred = rf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)'''
