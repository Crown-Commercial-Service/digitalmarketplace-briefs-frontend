import os
import hashlib
import jinja2
from dmutils.status import enabled_since, get_version_label
from dmutils.asset_fingerprint import AssetFingerprinter

basedir = os.path.abspath(os.path.dirname(__file__))


def get_asset_fingerprint(asset_file_path):
    hasher = hashlib.md5()
    with open(asset_file_path, 'rb') as asset_file:
        buf = asset_file.read()
        hasher.update(buf)
    return hasher.hexdigest()


class Config(object):

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    SESSION_COOKIE_NAME = 'dm_session'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True

    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    DM_DATA_API_URL = None
    DM_DATA_API_AUTH_TOKEN = None
    DM_NOTIFY_API_KEY = None

    NOTIFY_TEMPLATES = {
        'create_user_account': '1d1e38a6-744a-4d5a-84af-aefccde70a6c',
    }

    # This is just a placeholder
    ES_ENABLED = True

    DEBUG = False

    SECRET_KEY = None
    SHARED_EMAIL_KEY = None
    INVITE_EMAIL_SALT = 'InviteEmailSalt'

    STATIC_URL_PATH = '/buyers/static'
    ASSET_PATH = STATIC_URL_PATH + '/'
    BASE_TEMPLATE_DATA = {
        'header_class': 'with-proposition',
        'asset_path': ASSET_PATH,
        'asset_fingerprinter': AssetFingerprinter(asset_root=ASSET_PATH)
    }

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = False

    # LOGGING
    DM_LOG_LEVEL = 'DEBUG'
    DM_PLAIN_TEXT_LOGS = False
    DM_LOG_PATH = None
    DM_APP_NAME = 'briefs-frontend'

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        template_folders = [
            os.path.join(repo_root, 'app/templates')
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True
    DM_LOG_LEVEL = 'CRITICAL'
    WTF_CSRF_ENABLED = False

    DM_DATA_API_URL = "http://wrong.completely.invalid:5000"
    DM_DATA_API_AUTH_TOKEN = "myToken"

    DM_NOTIFY_API_KEY = "not_a_real_key-00000000-fake-uuid-0000-000000000000"
    SHARED_EMAIL_KEY = "KEY"
    SECRET_KEY = "KEY"

    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2016-11-29')


class Development(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True
    SESSION_COOKIE_SECURE = False

    DM_DATA_API_URL = "http://localhost:5000"
    DM_DATA_API_AUTH_TOKEN = "myToken"

    DM_NOTIFY_API_KEY = "not_a_real_key-00000000-fake-uuid-0000-000000000000"
    SECRET_KEY = "verySecretKey"
    SHARED_EMAIL_KEY = "very_secret"

    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2016-11-29')


class Live(Config):
    """Base config for deployed environments"""
    DEBUG = False
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'
    DM_HTTP_PROTO = 'https'

    # use of invalid email addresses with live api keys annoys Notify
    DM_NOTIFY_REDIRECT_DOMAINS_TO_ADDRESS = {
        "example.com": "success@simulator.amazonses.com",
        "example.gov.uk": "success@simulator.amazonses.com",
        "user.marketplace.team": "success@simulator.amazonses.com",
    }


class Preview(Live):
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-06')


class Staging(Live):
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-07')

    NOTIFY_TEMPLATES = {
        'create_user_account': '84f5d812-df9d-4ab8-804a-06f64f5abd30',
    }

    # Check we didn't forget any live template IDs
    assert NOTIFY_TEMPLATES.keys() == Config.NOTIFY_TEMPLATES.keys()


class Production(Live):
    FEATURE_FLAGS_NEW_SUPPLIER_FLOW = enabled_since('2017-02-08')

    NOTIFY_TEMPLATES = Staging.NOTIFY_TEMPLATES


configs = {
    'development': Development,
    'test': Test,

    'preview': Preview,
    'staging': Staging,
    'production': Production,
}
