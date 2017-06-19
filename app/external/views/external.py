from flask import Blueprint

external = Blueprint('external', __name__)


@external.route('/<framework_framework>/opportunities/<brief_id>')
def get_brief_by_id(framework_framework, brief_id):
    raise NotImplementedError()


@external.route('/create-user/<string:encoded_token>')
def create_user(encoded_token):
    raise NotImplementedError()


@external.route('/create-your-account-complete')
def create_your_account_complete():
    raise NotImplementedError()


@external.route('/login')
def render_login():
    raise NotImplementedError()
