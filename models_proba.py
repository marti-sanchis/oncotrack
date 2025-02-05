from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.role}')"

    # Password hash handling
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    nurse = db.relationship('User', foreign_keys=[nurse_id])

    def __repr__(self):
        return f"Patient('{self.name}', '{self.doctor_id}')"


