from flask import current_app, render_template, url_for, redirect, session, Blueprint

from dmapiclient.audit import AuditTypes
from dmutils.email import send_user_account_email
from dmutils.forms import get_errors_from_wtform

from app import data_api_client

from ..forms.auth_forms import EmailAddressForm

create_buyer = Blueprint('create_buyer', __name__)


@create_buyer.route('/create', methods=["GET"])
def create_buyer_account():
    form = EmailAddressForm()

    return render_template(
        "create_buyer/create_buyer_account.html",
        form=form), 200


@create_buyer.route('/create', methods=['POST'])
def submit_create_buyer_account():
    current_app.logger.info(
        "buyercreate: post create-buyer-account")
    form = EmailAddressForm()
    if form.validate_on_submit():
        email_address = form.email_address.data
        if not data_api_client.is_email_address_with_valid_buyer_domain(email_address):
            return render_template(
                "create_buyer/create_buyer_user_error.html",
                error='invalid_buyer_domain'), 400
        else:
            send_user_account_email(
                'buyer',
                email_address,
                current_app.config['NOTIFY_TEMPLATES']['create_user_account']
            )

            data_api_client.create_audit_event(
                audit_type=AuditTypes.invite_user,
                data={'invitedEmail': email_address}
            )

            return redirect(url_for('.create_your_account_complete'), 302)
    else:
        return render_template(
            "create_buyer/create_buyer_account.html",
            form=form,
            errors=get_errors_from_wtform(form),
            email_address=form.email_address.data
        ), 400


@create_buyer.route('/create-your-account-complete', methods=['GET'])
def create_your_account_complete():
    email_address = session.setdefault("email_sent_to", "the email address you supplied")
    return render_template(
        "create_buyer/create_your_account_complete.html",
        email_address=email_address), 200
