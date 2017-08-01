from flask.ext.wtf import Form
from wtforms import RadioField, BooleanField, validators


class AwardedSupplierForm(Form):
    """Form for the buyer to tell us which supplier was award a contract
    """
    # supplier choices expected to be set at runtime
    supplier = RadioField(
        "Winning Supplier",
        validators=[validators.DataRequired(message="You need to answer this question.")],
        coerce=int
    )

    def __init__(self, *args, **kwargs):
        """
            Requires extra keyword arguments:
             - `supplier_list` - list of suppliers for the multiple choice
        """
        super(AwardedSupplierForm, self).__init__(*args, **kwargs)

        # popping this kwarg so we don't risk it getting fed to wtforms default implementation which might use it
        # as a data field if there were a name collision
        suppliers = kwargs.pop("suppliers", [])
        self.supplier.choices = [(s['id'], s['name']) for s in suppliers]
        self.supplier.toolkit_macro_options = [{"value": s['id'], "label": s['name']} for s in suppliers]
