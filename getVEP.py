import requests

# URL de la API de Ensembl VEP para análisis de archivos
url = "https://rest.ensembl.org/vep/human/hgvs"

# Abrir el archivo VCF y enviarlo a la API
with open("mi_archivo.vcf", "rb") as file:
    response = requests.post(
        url,
        headers={"Content-Type": "text/plain"},
        data=file
    )

# Procesar la respuesta
if response.status_code == 200:
    resultado = response.json()
    for variante in resultado:
        for colocated in variante.get("colocated_variants", []):
            if "cosmic" in colocated["id"]:
                print(f"Variante: {variante['input']}, COSMIC ID: {colocated['id']}")
else:
    print(f"Error: {response.status_code}, {response.text}")
