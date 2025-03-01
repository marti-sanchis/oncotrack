from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, LoginManager, current_user, logout_user
from forms import LoginForm, SignUpForm
from models_proba import db, User, Patient, Variant, CancerType, Drug
from flask_bcrypt import Bcrypt
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

        # 🚀 Here, you would add logic to save the user to a database.

        new_user = User(name=name, surname=surname, email=form.email.data, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        print(f"New user: {name} {surname}, Role: {role}, Email: {email}")  # Debugging
        return redirect(url_for('userspace'))  # Redirect after successful signup

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
    gender_map = {"female": "F", "male": "M", "other": "Other"} 
    gender = gender_map.get(request.form.get("gender").lower(), "Other")
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
        process_vcf(new_patient.patient_id, file_path)
        
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
    possible_treatments = Drug.query.all()  # Assuming you have a table of treatments
    return render_template('choose_treatment.html', patient=patient, treatments=possible_treatments)

@app.route('/assign_treatment/<int:patient_id>', methods=['POST'])
@login_required
def assign_treatment(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    drug_id = request.form.get('drug_id')
    
    if drug_id:
        treatment = Drug.query.get(drug_id)
        if treatment:
            patient.treatment = treatment.name  # Assuming 'treatment' is a column in Patient
            db.session.commit()
            flash(f'Treatment {treatment.name} assigned to {patient.name}', 'success')

    return redirect(url_for('doctor_space'))  # Redirect back to the doctor page


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