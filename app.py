from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, login_required, LoginManager, current_user, logout_user
from forms import LoginForm, SignUpForm
from models_proba import db, User, Patient, Variant, Gene, CancerType, Drug, DrugAssociation, patient_has_variant
from flask_bcrypt import Bcrypt
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
from config import Config
from werkzeug.utils import secure_filename
import os
from vcf_reader import process_vcf

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


# ✅ 4. Load user function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Converts user_id to integer and fetches 

@app.route("/")
def home():
    return render_template("home.html")


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

        # Guardamos el usuario en la base de datos
        new_user = User(name=name, surname=surname, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        # Redirigir según el rol del usuario
        if role == 'doctor':
            return redirect(url_for('doctor_space'))
        elif role == 'nurse':
            return redirect(url_for('nurse_space'))
        else:
            return redirect(url_for('index'))  # O cualquier otra página por defecto

    return render_template('auth/signup.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
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
    doctor_patients = Patient.query.filter_by(doctor_id=current_user.id).all()
    cancer_types = CancerType.query.all()

    # Obtener todos los usuarios con rol "Nurse"
    nurses = User.query.filter_by(role="nurse").all()

    return render_template(
        'doctor_space.html', 
        user=current_user, 
        patients=doctor_patients, 
        cancer_types=cancer_types,
        nurses=nurses
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
        nurse_id=nurse_id
    )

    # Agregar paciente a la base de datos y hacer commit
    try:
        db.session.add(new_patient)
        db.session.commit()

        # Process VCF
        process_vcf(file_path, new_patient.patient_id)
        
        flash("Patient added successfully!", "success")
        print("Paciente añadido correctamente")
    except Exception as e:
        db.session.rollback()  # En caso de error, hacer rollback
        flash(f"Error adding patient: {e}", "danger")
        print("Error al añadir paciente:", str(e))

    return redirect(url_for('doctor_space', cancer_types=cancer_types, nurses=nurses))


@app.route('/choose_treatment/<int:patient_id>')
@login_required
def choose_treatment(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    treatments = Drug.query.all()  # Fetch all drugs/treatments
    
    # Return the patient details and drug names in JSON format
    return render_template('choose_treatment.html', patient=patient, treatments=treatments)


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

    ### TREATMENTS
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
            match_reason = "Cancer type"  # Por defecto, solo coincide por cáncer
            name = ""

        elif association == "specific":
            if t_variant_id in variant_ids:
                match_reason = "Variant"  # Mostramos el variant_id
                name = t_variant_id
            elif t_gene_id in gene_ids:
                match_reason = "Gene"  # Mostramos el gene_id
                gene_symbol = db.session.query(Gene.gene_symbol).filter(Gene.gene_id == t_gene_id).first()
                name = gene_symbol[0]

        # Evitar duplicados y dar prioridad a la mejor coincidencia
        if drug_name in treatments_dict:
            existing_reason = treatments_dict[drug_name][3]
            priority_order = {"Cancer type": 1, "Gene": 2, "Variant": 3}
            
            if priority_order.get(existing_reason, 0) < priority_order.get(match_reason, 0):
                treatments_dict[drug_name] = (drug_name, association, subtype, match_reason, name)
        else:
            treatments_dict[drug_name] = (drug_name, association, subtype, match_reason, name)

    # Convertimos el diccionario en una lista de tratamientos únicos
    treatments = list(treatments_dict.values())

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

    txt_filename = f"KEGG_2021_Human.human.enrichr.reports.txt"
    txt_file_path = os.path.join(f"enrichr_results/Patient_{patient.patient_id}", txt_filename)

    table_data = []
    if os.path.exists(txt_file_path):
        with open(txt_file_path, 'r') as file:
            lines = file.readlines()[1:11]
            for line in lines:
                columns = line.strip().split("\t")
                if len(columns) > 1: 
                    selected_columns = [columns[1], columns[2], columns[4], columns[9].replace(";", " ")] 
                    table_data.append(selected_columns)
    else:
        print(f"File {txt_filename} not found.")

    return render_template(
        'patient_details.html', 
        patient=patient, 
        variant_details=variant_details, 
        treatments=treatments, 
        user_id=current_user.id, 
        cancer_types=cancer_types, 
        resistances=resistances,
        table_data=table_data 
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