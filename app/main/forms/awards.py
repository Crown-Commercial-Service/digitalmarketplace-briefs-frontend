from flask.ext.wtf import Form
from wtforms import RadioField, validators


class AwardedBriefResponseForm(Form):
    """Form for the buyer to tell us which BriefResponse was awarded a contract
    """
    # BriefResponse choices expected to be set at runtime
    brief_response = RadioField(
        "Winning BriefResponse",
        validators=[validators.DataRequired(message="You need to answer this question.")],
        coerce=int
    )

    def __init__(self, brief_responses, *args, **kwargs):
        """
            Requires extra argument:
             - `brief_responses` - list of BriefResponses for the multiple choice
        """
        super(AwardedBriefResponseForm, self).__init__(*args, **kwargs)

        brief_responses = list(
            sorted(
                [{'id': b['id'], 'name': b['supplierName']} for b in brief_responses],
                key=lambda x: x['name']
            )
        )

        self.brief_response.choices = [(br['id'], br['name']) for br in brief_responses]
        self.brief_response.toolkit_macro_options = [{"value": br['id'], "label": br['name']} for br in brief_responses]
