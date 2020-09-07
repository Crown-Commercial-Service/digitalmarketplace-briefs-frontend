from flask import Flask, request, redirect, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

import dmapiclient
import dmcontent.govuk_frontend
from dmutils import init_app
from dmutils.user import User

from config import configs


login_manager = LoginManager()
data_api_client = dmapiclient.DataAPIClient()
csrf = CSRFProtect()


def create_app(config_name):
    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        login_manager=login_manager,
    )

    from .metrics import metrics as metrics_blueprint, gds_metrics
    from .create_buyer.views.create_buyer import create_buyer as create_buyer_blueprint
    from .main import dos as dos_blueprint
    from dmutils.external import external as external_blueprint
    from .main import main as main_blueprint
    from .status import status as status_blueprint

    application.register_blueprint(metrics_blueprint, url_prefix='/buyers')
    application.register_blueprint(create_buyer_blueprint, url_prefix='/buyers')
    application.register_blueprint(dos_blueprint, url_prefix='/buyers')
    application.register_blueprint(main_blueprint, url_prefix='/buyers')
    application.register_blueprint(status_blueprint, url_prefix='/buyers')

    # Must be registered last so that any routes declared in the app are registered first (i.e. take precedence over
    # the external NotImplemented routes in the dm-utils external blueprint).
    application.register_blueprint(external_blueprint)

    login_manager.login_view = 'external.render_login'
    login_manager.login_message = None  # don't flash message to user
    gds_metrics.init_app(application)
    csrf.init_app(application)

    # We want to be able to access this function from within all templates
    application.jinja_env.globals["govuk_frontend_from_question"] = (
        dmcontent.govuk_frontend.from_question
    )

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            if request.query_string:
                return redirect(
                    '{}?{}'.format(
                        request.path[:-1],
                        request.query_string.decode('utf-8')
                    ),
                    code=301
                )
            else:
                return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
