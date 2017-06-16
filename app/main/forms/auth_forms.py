from flask_wtf import Form
from wtforms.validators import DataRequired, Regexp
from dmutils.forms import StripWhitespaceStringField


class EmailAddressForm(Form):
    email_address = StripWhitespaceStringField(
        'Email address', id="input_email_address",
        validators=[
            DataRequired(message="You must provide an email address"),
            Regexp("^[^@^\s]+@[^@^\.^\s]+(\.[^@^\.^\s]+)+$",
                   message="You must provide a valid email address")
        ]
    )
