from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from dmutils.forms.fields import DMStripWhitespaceStringField
from dmutils.forms.validators import EmailValidator as ValidEmailAddress


class EmailAddressForm(FlaskForm):
    email_address = DMStripWhitespaceStringField(
        "Your email address",
        validators=[
            DataRequired(message="Enter an email address"),
            ValidEmailAddress(message="Enter an email address in the correct format, like name@example.gov.uk"),
        ]
    )
