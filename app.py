from flask import Flask, render_template, request
from forms import LoginForm, SignUpForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Required for CSRF protection

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

        # 🚀 Here, you would add logic to save the user to a database.

        new_user = User(email=form.email.data, password=hashed_password, role=role)
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
            if (form_password := form.password.data):
                if bcrypt.checkpw(form_password.encode('utf8'), user.password):
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
        return render_template('doctor_userspace.html', user=current_user)
    elif current_user.role == 'nurse':
        return render_template('nurse_userspace.html', user=current_user)
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

if __name__ == "__main__":
    app.run(debug=True)
