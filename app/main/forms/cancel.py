from flask.ext.wtf import Form
from wtforms import RadioField, validators


class CancelBriefForm(Form):
    """Form for the buyer to tell us why they are cancelling the requirement
    """
    choices = [
        ('cancel', 'The requirement has been cancelled'),
        ('unsuccessful', 'There were no suitable suppliers'),
    ]
    cancel_reason = RadioField(
        validators=[validators.InputRequired(message='You need to answer this question.')],
        choices=choices
    )

    def __init__(self, brief, label_text, *args, **kwargs):
        super(CancelBriefForm, self).__init__(*args, **kwargs)
        brief_name = brief.get('title', brief.get('lotName', ''))
        self.cancel_reason.label.text = label_text.format(brief_name)
        self.cancel_reason.toolkit_macro_options = [{'value': i[0], 'label': i[1]} for i in self.choices]
