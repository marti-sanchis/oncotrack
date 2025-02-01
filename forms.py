from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Email, InputRequired, Length, ValidationError

class SignUpForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=80)],
                       render_kw={"placeholder": "Mary"})

    surname = StringField(validators=[InputRequired(), Length(min=1, max=80)],
                          render_kw={"placeholder": "Rose"})
    
    email = StringField(validators=[Email(), InputRequired(), Length(min=4, max=80)],
                        render_kw={"placeholder": "name@example.com"})

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("This email address is already in use please choose different one.")

    password = PasswordField(validators=[InputRequired(), Length(min=4, max=80)],
                             render_kw={"placeholder": "Password"})

    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    email = StringField(validators=[Email(), InputRequired(), Length(min=4, max=80)],
                        render_kw={"placeholder": "name@example.com"})

    password = PasswordField(validators=[InputRequired(), Length(min=4, max=80)],
                             render_kw={"placeholder": "Password"})

    submit = SubmitField("Log in")