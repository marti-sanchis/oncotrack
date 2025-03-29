from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_login import login_user, login_required, LoginManager, current_user, logout_user
from forms import LoginForm, SignUpForm
from models_proba import db, User, Patient, Variant, Gene, CancerType, Drug, DrugAssociation, patient_has_variant, patient_has_drug, patient_has_signature, MutationalSignature
from flask_bcrypt import Bcrypt
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
from config import Config
from werkzeug.utils import secure_filename
import os
from vcf_reader import process_vcf
from threading import Thread

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ✅ 2. Initialize Bcrypt AFTER defining app
bcrypt = Bcrypt(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect to 'login' if user is not logged in

UPLOAD_FOLDER = 'uploads'  # Carpeta donde guardar temporalmente el archivo
ALLOWED_EXTENSIONS = {'vcf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Función para verificar extensión del archivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to process vcf file in a subprocess
def process_vcf_async(app, file_path, patient_id):
    with app.app_context(): 
        process_vcf(file_path, patient_id)
        patient = Patient.query.get(patient_id)
        if patient:
            patient.status = "completed"
            db.session.commit()

# Función para extraer la lista de tratamientos de cada paciente
def get_filtered_treatments(patient):
    """Filtra y devuelve la lista de tratamientos recomendados para un paciente"""
    cancer_id = patient.cancer_id
    variant_ids = [v.variant_id for v in patient.variants]  # Lista de variantes del paciente
    gene_ids = [v.gene_id for v in db.session.query(Variant.gene_id).filter(Variant.variant_id.in_(variant_ids)).all()]

    # Consulta a la base de datos para obtener los tratamientos filtrados
    treatment_results = db.session.query(
        Drug.name, 
        DrugAssociation.association, 
        DrugAssociation.subtype,
        DrugAssociation.cancer_id,
        DrugAssociation.variant_id,
        DrugAssociation.gene_id
    ).join(DrugAssociation).filter(
        or_(
            and_(
                DrugAssociation.cancer_id == cancer_id,
                DrugAssociation.association == "generic"
            ),
            and_(
                DrugAssociation.cancer_id == cancer_id,
                DrugAssociation.variant_id.in_(variant_ids),
                DrugAssociation.association == "specific"
            ),
            and_(
                DrugAssociation.cancer_id == cancer_id,
                DrugAssociation.gene_id.in_(gene_ids),
                DrugAssociation.association == "specific"
            )
        )
    ).filter(DrugAssociation.association != "resistance").all()

    # Diccionario para evitar duplicados y priorizar el mejor match_reason
    treatments_dict = {}

    for treatment in treatment_results:
        drug_name, association, subtype, t_cancer_id, t_variant_id, t_gene_id = treatment

        if association == "generic":
            match_reason = "Cancer type"
            name = ""
        elif association == "specific":
            if t_variant_id in variant_ids:
                match_reason = "Variant"
                name = t_variant_id
            elif t_gene_id in gene_ids:
                match_reason = "Gene"
                gene_symbol = db.session.query(Gene.gene_symbol).filter(Gene.gene_id == t_gene_id).first()
                name = gene_symbol[0] if gene_symbol else ""

        # Evitar duplicados y priorizar el mejor match_reason
        if drug_name in treatments_dict:
            existing_reason = treatments_dict[drug_name][3]
            priority_order = {"Cancer type": 1, "Gene": 2, "Variant": 3}
            if priority_order.get(existing_reason, 0) < priority_order.get(match_reason, 0):
                treatments_dict[drug_name] = (drug_name, association, subtype, match_reason, name)
        else:
            treatments_dict[drug_name] = (drug_name, association, subtype, match_reason, name)

    # Convertir diccionario a lista
    return list(treatments_dict.values())

# Load user function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Converts user_id to integer and fetches 

@app.route("/")
def home():
    return render_template("home.html")
def index():
    # Obtener pacientes no archivados
    patients = Patient.query.filter_by(archived=False).all()
    return render_template('index.html', patients=patients)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        name = form.name.data
        surname = form.surname.data
        email = form.email.data
        password = form.password.data     
        role = form.role.data

        # Hash the password before saving it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Save the user in the database
        new_user = User(name=name, surname=surname, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        # Log in the user immediately after signup
        login_user(new_user)

        # Redirect directly to the corresponding space based on role
        if role == 'doctor':
            flash('Successfully signed up and logged in as a doctor!', 'success')
            return redirect(url_for('doctor_space'))
        elif role == 'nurse':
            flash('Successfully signed up and logged in as a nurse!', 'success')
            return redirect(url_for('nurse_space'))
        else:
            flash('Successfully signed up!', 'success')
            return redirect(url_for('index'))  # Default redirect if no specific role

    return render_template('auth/signup.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # If user does not exist, flash a message and redirect to signup
        if not user:
           # Pass email to template to pre-fill signup form if desired
            return render_template('auth/login.html', 
                                   form=form, 
                                   user_not_found=True, 
                                   email=form.email.data)
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            if user.role == 'doctor':
                return redirect(url_for('doctor_space'))
            elif user.role == 'nurse':
                return redirect(url_for('nurse_space'))
            else:
                return redirect(url_for('userspace'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('auth/login.html', form=form)


@app.route('/userspace', methods=['GET', 'POST'])
@login_required
def userspace():
    # Create a form for patient data
    form = SignUpForm()  # Or create a new PatientForm if you have one

    # Process form submission
    if form.validate_on_submit():
        # Handle form submission (e.g., add patient or handle data)
        flash("Patient data submitted successfully!", "success")
        return redirect(url_for('userspace'))  # Redirect after form submission

    cancer_types = CancerType.query.all()

    # Render the template with the form
    if current_user.role == 'doctor':
        return render_template('doctor_space.html', user=current_user, form=form, cancer_types=cancer_types)
    elif current_user.role == 'nurse':
        return render_template('nurse_space.html', user=current_user, form=form, cancer_types=cancer_types)
    else:
        return redirect(url_for('home'))  # Redirect to home if not doctor or nurse


@app.route('/doctor_space')
@login_required
def doctor_space():
    if current_user.role != 'doctor':
        return redirect(url_for('home'))

    # Obtener todos los pacientes asignados al doctor actual
    doctor_patients = Patient.query.filter_by(doctor_id=current_user.id, archived=False).all()
    cancer_types = CancerType.query.all()

    # Obtener todos los usuarios con rol "Nurse"
    nurses = User.query.filter_by(role="nurse").all()

    patients_with_treatments = {}

    for patient in doctor_patients:
        treatments = get_filtered_treatments(patient)  # 🔹 Obtener tratamientos para cada paciente
        patients_with_treatments[patient] = treatments

    print(patients_with_treatments)

    return render_template(
        'doctor_space.html', 
        user=current_user, 
        patients=doctor_patients, 
        cancer_types=cancer_types,
        nurses=nurses,
        patients_with_treatments=patients_with_treatments
    )

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    print(request.form)
    if current_user.role != 'doctor':
        return redirect(url_for('home'))

    cancer_types = CancerType.query.all()
    nurses = User.query.filter_by(role='nurse').all()

    # Obtener datos del formulario
    if request.method == 'POST':
        patient_name = request.form.get('patient_name', '').strip()
        DNI = request.form.get('dni', '').strip()
        gender = request.form.get('gender', '').strip()
        age = request.form.get('age', '').strip()
        phone = request.form.get('phone', None)
        email = request.form.get('email', None)
        cancer_type_id = request.form.get('cancer_type', None)
        nurse_id = request.form.get('nurse_id', None)
        vcf_file = request.files.get('vcf_file')

    # Validación para evitar datos vacíos
    if not patient_name or not DNI or not age or not cancer_type_id or not vcf_file:
        flash("All required fields must be filled", "danger")
        return redirect(url_for('doctor_space'))

    # Convertir age a entero y verificar que sea un número válido
    try:
        age = int(age)
        if age <= 0:
            flash("Age must be a positive number", "danger")
            return redirect(url_for('doctor_space'))
    except ValueError:
        flash("Age must be a number", "danger")
        return redirect(url_for('doctor_space'))

    # Convertir "female" -> "F", "male" -> "M", "other" -> "Other"
    gender = request.form.get("gender", "Other").strip()
    print(f"Valor de 'gender' antes de la inserción: {gender}")

    # Verificar si el tipo de cáncer existe
    cancer_type = CancerType.query.get(cancer_type_id)
    if not cancer_type:
        flash("Invalid cancer type selected", "danger")
        return redirect(url_for('doctor_space'))

    # Verificar si el nurse_id es válido
    if nurse_id:
        nurse = User.query.get(nurse_id)
        if not nurse or nurse.role != 'nurse':
            flash("Invalid nurse selected", "danger")
            return redirect(url_for('doctor_space'))
    else:
        nurse_id = None  # Permitir que no haya enfermero asignado

    if vcf_file and allowed_file(vcf_file.filename):
        filename = secure_filename(vcf_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        vcf_file.save(file_path)

    # Crear y agregar nuevo paciente
    new_patient = Patient(
        name=patient_name,
        DNI=DNI,
        gender=gender,
        age=age,
        phone=phone,
        email=email,
        cancer_id=cancer_type.cancer_id,
        doctor_id=current_user.id,  # Asegurarse de que el paciente tenga un doctor asignado
        nurse_id=nurse_id,
        status="processing"
    )

    # Agregar paciente a la base de datos y hacer commit
    try:
        db.session.add(new_patient)
        db.session.commit()
        print(f"App en add_patient: {app}")
        print(f"File path: {file_path}")
        print(f"Patient ID: {new_patient.patient_id}")  # Verifica que existe

        # Process VCF
        print("App en add_patient:", app)
        thread = Thread(target=process_vcf_async, args=(app, file_path, new_patient.patient_id))
        thread.start()
        
        flash("Patient added successfully!", "success")
        print("Paciente añadido correctamente")
    except Exception as e:
        db.session.rollback()  # En caso de error, hacer rollback
        flash(f"Error adding patient: {e}", "danger")
        print("Error al añadir paciente:", str(e))

    return redirect(url_for('doctor_space', cancer_types=cancer_types, nurses=nurses))


@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    # Asegurarse de que el usuario es un doctor
    if current_user.role != 'doctor':
        flash('You do not have permission to delete a patient.', 'danger')
        return redirect(url_for('doctor_space'))

    patient = Patient.query.get(patient_id)
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('doctor_space'))

    action = request.form.get('action')
    if action == 'delete':
        try:
            db.session.query(patient_has_variant).filter(patient_has_variant.c.patient_id == patient_id).delete()
            try: 
                db.session.query(patient_has_signature).filter(patient_has_signature.c.patient_id == patient_id).delete()
            except:
                print("continue")
            try:
                db.session.query(patient_has_drug).filter(patient_has_drug.c.patient_id == patient_id).delete()
            except:
                print("continue")

            #Eliminar el paciente de la tabla Patient
            db.session.delete(patient)
            db.session.commit()

            flash('Patient and all related data have been successfully deleted.', 'success')

        except Exception as e:
            db.session.rollback()
            print(f'Error deleting patient: {e}', 'danger')

    elif action == 'archive':
        # Archivar al paciente (marcar como archivado)
        patient.archived = True
        db.session.commit()
        flash('Patient archived', 'info')

    return redirect(url_for('doctor_space'))


@app.route('/archived_patients')
def archived_patients():
    # Obtener la lista de pacientes archivados
    archived_patients = Patient.query.filter_by(archived=True).all()
    cancer_types = CancerType.query.all()
    return render_template('archived_patients.html', 
        archived_patients=archived_patients,
        cancer_types = cancer_types)


@app.route('/unarchive_patient/<int:patient_id>', methods=['POST'])
@login_required
def unarchive_patient(patient_id):
    if current_user.role != 'doctor':
        return redirect(url_for('home'))

    # Buscar al paciente
    patient = Patient.query.get(patient_id)

    if patient and patient.archived:  # Verificar si el paciente está archivado
        patient.archived = False  # Cambiar su estado a no archivado
        db.session.commit()  # Guardar los cambios en la base de datos

        flash('Patient has been unarchived successfully.', 'success')
    else:
        flash('Patient not found or already unarchived.', 'danger')

    return redirect(url_for('doctor_space'))  # Redirigir a la lista de pacientes del doctor


@app.route('/check_patient_status/<int:patient_id>')
def check_patient_status(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        return jsonify({"status": patient.status})
    return jsonify({"status": "not_found"}), 404


@app.route('/assign_treatment', methods=['POST'])
@login_required
def assign_treatment():
    patient_id = request.form.get('patient_id')
    treatment_name = request.form.get('treatment_id')  # Esto es el nombre del tratamiento

    print(f"Form submitted to /assign_treatment")
    print(f"Patient ID: {patient_id}, Treatment Name: {treatment_name}")  # Verifica estos valores

    # Verificar que el paciente y el tratamiento existan
    patient = Patient.query.get_or_404(patient_id)
    treatment = Drug.query.filter_by(name=treatment_name).first()  # Buscar por nombre del tratamiento

    if not treatment:
        flash('Treatment not found!', 'danger')
        return redirect(url_for('doctor_space'))  # Redirigir si no se encuentra el tratamiento

    # Eliminar cualquier tratamiento previo asignado a este paciente
    db.session.execute(
        patient_has_drug.delete().where(patient_has_drug.c.patient_id == patient_id)
    )
    db.session.commit()

    # Asociar el paciente con el nuevo tratamiento en la tabla relacional
    patient_has_drug_entry = patient_has_drug.insert().values(patient_id=patient.patient_id, drug_id=treatment.drug_id)
    db.session.execute(patient_has_drug_entry)
    db.session.commit()

    flash('Treatment assigned successfully!', 'success')
    return redirect(url_for('doctor_space'))  # Redirigir a la página del doctor


@app.route('/analysis_results/<int:patient_id>/sigProfiler/<path:filename>')
@login_required

def serve_analysis_file(patient_id, filename):
    file_path = f"analysis_results/Patient_{patient_id}/sigProfiler/{filename}"
    return send_file(file_path)

@app.route('/patient_details/<int:patient_id>')
@login_required

def patient_details(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return "Patient not found", 404

    cancer_types = CancerType.query.all()
    cancer_id = patient.cancer_id 

    variants = db.session.query(Variant).join(patient_has_variant).filter(patient_has_variant.c.patient_id == patient_id).all()
    variant_details = []
    for variant in variants:
        gene_symbol = db.session.query(Gene.gene_symbol).filter(Gene.gene_id == variant.gene_id).first()
        gene_symbol = gene_symbol[0] if gene_symbol else "Unknown Gene"
        variant_details.append({
            'variant_id': variant.variant_id,
            'gene_symbol': gene_symbol,
            'chromosome': variant.chromosome,
            'aa_mutation': variant.aa_mutation,
            'variant_type': variant.variant_type
        })

    variant_ids = [variant.variant_id for variant in variants]
    gene_ids = [variant.gene_id for variant in variants]

    print(f"Patient Variants: {variant_ids}")  # Lista de variant_id del paciente
    print(f"Patient Genes: {gene_ids}")  # Lista de gene_id del paciente

    treatments = get_filtered_treatments(patient)

    ### RESISTANCES
    resistances = db.session.query(
        Drug.name, 
        DrugAssociation.association,
        DrugAssociation.variant_id,
        DrugAssociation.gene_id
    ).join(DrugAssociation).filter(DrugAssociation.association == 'resistance').filter(
        or_(
            DrugAssociation.variant_id.in_(variant_ids),
            DrugAssociation.gene_id.in_(gene_ids)
            )
        )

    # Agregar información adicional
    resistance_data = {}
    priority_order = {"Gene": 1, "Variant": 2}
    for resistance in resistances:
        drug_name, association, variant_id, gene_id = resistance
        # Aquí determinamos la razón del match
        match_reason = None
        if variant_id in variant_ids:
            match_reason = "Variant"
            name = variant_id
        elif gene_id in gene_ids:
            match_reason = "Gene"
            gene_symbol = db.session.query(Gene.gene_symbol).filter(Gene.gene_id == gene_id).first()
            name = gene_symbol[0]

        if drug_name in resistance_data:
            existing_reason = resistance_data[drug_name][1]
            if priority_order.get(existing_reason, 0) < priority_order.get(match_reason, 0):
                resistance_data[drug_name] = (drug_name, match_reason, name)
            elif resistance_data[drug_name][1] == match_reason:
                if resistance_data[drug_name][2] != name:
                    resistance_data[drug_name] = (drug_name, match_reason, f"{resistance_data[drug_name][2]}, {name}")
        else:
            resistance_data[drug_name] = (drug_name, match_reason, name)
            print(f"===> {resistance_data[drug_name]}")

        resistances = list(resistance_data.values())

    enrichr_txt_path = f"analysis_results/Patient_{patient.patient_id}/enrichment/KEGG_2021_Human.human.enrichr.reports.txt"

    table_data = []
    if os.path.exists(enrichr_txt_path):
        with open(enrichr_txt_path, 'r') as file:
            lines = file.readlines()[1:11]
            for line in lines:
                columns = line.strip().split("\t")
                if len(columns) > 1: 
                    selected_columns = [columns[1], columns[2], columns[4], columns[9].replace(";", " ")] 
                    table_data.append(selected_columns)
    else:
        print(f"Enrichr txt output not found.")

    # MUTATIONAL SIGNATURES
    signatures = db.session.query(
        MutationalSignature.signature_id,
        MutationalSignature.aetiology,
        MutationalSignature.comments,
        MutationalSignature.link
    ).join(
        patient_has_signature,
        MutationalSignature.signature_id == patient_has_signature.c.signature_id
    ).filter(
        patient_has_signature.c.patient_id == patient_id
    ).all()
    
    # Convert to list of dictionaries for easier template access
    signature_details = []
    for sig in signatures:
        signature_details.append({
            'signature_id': sig.signature_id,
            'aetiology': sig.aetiology,
            'comments': sig.comments,
            'link': sig.link,
        })

    return render_template(
        'patient_details.html', 
        patient=patient, 
        variant_details=variant_details, 
        treatments=treatments, 
        user_id=current_user.id, 
        cancer_types=cancer_types, 
        resistances=resistances,
        table_data=table_data,
        signature_details=signature_details
    )


@app.route('/nurse_space')
@login_required
def nurse_space():
    if current_user.role != 'nurse':
        return redirect(url_for('home'))  # Redirige a home si no es nurse

    nurse = User.query.filter_by(id=current_user.id).first()
    if nurse:
        # Obtener los pacientes asignados a la enfermera
        nurse_patients = Patient.query.filter_by(nurse_id=current_user.id).all()
    else:
        nurse_patients = []

    cancer_types = CancerType.query.all()

    # Renderizar la plantilla con la lista de pacientes (solo lectura)
    return render_template(
        'nurse_space.html', 
        user=current_user, 
        patients=nurse_patients,
        cancer_types=cancer_types
        )


@app.route('/logout')
@login_required  # Optional, depending on whether you want to restrict logout to logged-in users
def logout():
    logout_user()
    return redirect(url_for('home'))  # Redirect to a page after logout (e.g., home page)

if __name__ == "__main__":
    app.run(debug=True)