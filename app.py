from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, LoginManager, current_user, logout_user
from forms import LoginForm, SignUpForm
from models_proba import db, User, Patient, Variant
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import sessionmaker
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ✅ 2. Initialize Bcrypt AFTER defining app
bcrypt = Bcrypt(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect to 'login' if user is not logged in

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
    loginerror = None
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if form.password.data:
                if bcrypt.check_password_hash(user.password, form.password.data):
                    login_user(user)
                    # Redirigir dependiendo del rol del usuario
                    if user.role == 'doctor':
                        return redirect(url_for('doctor_space'))
                    elif user.role == 'nurse':
                        return redirect(url_for('nurse_space'))
        loginerror = "Invalid email or password."
    return render_template('auth/login.html', form=form, loginerror=loginerror)

@app.route('/userspace', methods=['GET', 'POST'])
@login_required
def userspace():
    if current_user.role == 'doctor':
        return render_template('doctor_space.html', user=current_user)
    elif current_user.role == 'nurse':
        return render_template('nurse_space.html', user=current_user)
    else:
        return redirect(url_for('home'))  # Redirige a la página de inicio si no es doctor ni enfermero


@app.route('/doctor_space', methods=['GET', 'POST'])
@login_required
def doctor_space():
    if current_user.role != 'doctor':
        return redirect(url_for('home'))  # Redirige a home si no es doctor

    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        if patient_name:
            new_patient = Patient(name=patient_name, doctor_id=current_user.id)
            db.session.add(new_patient)
            db.session.commit()

    # Obtener los pacientes del doctor
    doctor_patients = Patient.query.filter_by(doctor_id=current_user.id).all()

    return render_template('doctor_space.html', user=current_user, patients=doctor_patients)


@app.route('/nurse_space', methods=['GET'])
@login_required
def nurse_space():
    if current_user.role != 'nurse':
        return redirect(url_for('home'))  # Redirige a home si no es nurse

    # Obtener los pacientes asignados a la enfermera
    assigned_patients = Patient.query.filter_by(nurse_id=current_user.id).all()

    # Renderizar la plantilla con la lista de pacientes (solo lectura)
    return render_template('nurse_space.html', user=current_user, patients=assigned_patients)

@app.route('/add_patient', methods=['POST'])
@login_required
def add_patient():
    if current_user.role != 'doctor':
        return redirect(url_for('home'))  # Redirige a home si no es doctor
    
    # Obtener el nombre del paciente del formulario
    patient_name = request.form.get('patient_name')

    if not patient_name:
        flash('Patient name is required!', 'error')  # Mostrar mensaje de error si el campo está vacío
        return redirect(url_for('doctor_space'))

    # Crear una nueva instancia del paciente
    new_patient = Patient(name=patient_name, doctor_id=current_user.id)
    
    # Guardar el paciente en la base de datos
    db.session.add(new_patient)
    db.session.commit()

    flash(f'Patient "{patient_name}" added successfully!', 'success')  # Mensaje de éxito
    
    # Redirigir al espacio del doctor después de agregar el paciente
    return redirect(url_for('doctor_space'))

@app.route('/logout')
@login_required  # Optional, depending on whether you want to restrict logout to logged-in users
def logout():
    logout_user()
    return redirect(url_for('home'))  # Redirect to a page after logout (e.g., home page)

if __name__ == "__main__":
    app.run(debug=True)
