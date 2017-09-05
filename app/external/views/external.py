from flask import Blueprint

external = Blueprint('external', __name__)


@external.route('/<framework_framework>/opportunities/<brief_id>')
def get_brief_by_id(framework_framework, brief_id):
    raise NotImplementedError()


@external.route('/user/create/<string:encoded_token>')
def create_user(encoded_token):
    raise NotImplementedError()


@external.route('/user/login')
def render_login():
    raise NotImplementedError()
