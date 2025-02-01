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
        # 🚀 Here, you would add logic to save the user to a database.
        print(f"New user: {name} {surname}, Email: {email}")  # Debugging
        return redirect(url_for('home'))  # Redirect after successful signup

    return render_template('auth/signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Create an instance of the form
    if form.validate_on_submit():
        # Process login (this is just a placeholder)
        return "Login successful"
    return render_template('auth/login.html', form=form)



if __name__ == "__main__":
    app.run(debug=True)
