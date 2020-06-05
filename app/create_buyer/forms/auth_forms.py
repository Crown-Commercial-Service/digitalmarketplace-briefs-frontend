from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from dmutils.forms.fields import DMStripWhitespaceStringField
from dmutils.forms.validators import EmailValidator as ValidEmailAddress


class EmailAddressForm(FlaskForm):
    email_address = DMStripWhitespaceStringField(
        "",
        validators=[
            DataRequired(message="email_address_data_required"),
            ValidEmailAddress(message="email_address_invalid_email_address"),
        ]
    )
