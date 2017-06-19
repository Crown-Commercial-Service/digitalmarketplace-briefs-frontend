import six

from flask import current_app, render_template, url_for, abort, redirect, session, Blueprint

from dmapiclient.audit import AuditTypes
from dmutils.email import generate_token, send_email
from dmutils.email.exceptions import EmailError
from dmutils.email.helpers import hash_string

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
            token = generate_token(
                {
                    "email_address":  email_address
                },
                current_app.config['SHARED_EMAIL_KEY'],
                current_app.config['INVITE_EMAIL_SALT']
            )
            url = url_for('external.create_user', encoded_token=token, _external=True)
            email_body = render_template("emails/create_buyer_user_email.html", url=url)

            try:
                send_email(
                    email_address,
                    email_body,
                    current_app.config['DM_MANDRILL_API_KEY'],
                    current_app.config['CREATE_USER_SUBJECT'],
                    current_app.config['RESET_PASSWORD_EMAIL_FROM'],
                    current_app.config['RESET_PASSWORD_EMAIL_NAME'],
                    ["user-creation"]
                )
                session['email_sent_to'] = email_address
            except EmailError as e:
                current_app.logger.error(
                    "buyercreate.fail: Create user email failed to send. "
                    "error {error} email_hash {email_hash}",
                    extra={
                        'error': six.text_type(e),
                        'email_hash': hash_string(email_address)})
                abort(503, response="Failed to send user creation email.")

            data_api_client.create_audit_event(
                audit_type=AuditTypes.invite_user,
                data={'invitedEmail': email_address})

            return redirect(url_for('external.create_your_account_complete'), 302)
    else:
        return render_template(
            "create_buyer/create_buyer_account.html",
            form=form,
            email_address=form.email_address.data
        ), 400
