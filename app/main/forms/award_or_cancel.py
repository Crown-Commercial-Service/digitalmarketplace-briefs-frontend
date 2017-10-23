from flask.ext.wtf import Form
from wtforms import RadioField, validators


class AwardOrCancelBriefForm(Form):
    """Form for the buyer to tell us whether they want to award or cancel the requirements
    """
    choices = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('back', 'We are still evaluating suppliers'),
    ]
    award_or_cancel_decision = RadioField(
        validators=[validators.InputRequired(message='You need to answer this question.')],
        choices=choices
    )

    def __init__(self, brief, *args, **kwargs):
        super(AwardOrCancelBriefForm, self).__init__(*args, **kwargs)
        brief_name = brief.get('title', brief.get('lotName', ''))
        self.award_or_cancel_decision.label.text = "Have you awarded a contract for {}?".format(brief_name)
        self.award_or_cancel_decision.toolkit_macro_options = [{'value': i[0], 'label': i[1]} for i in self.choices]
