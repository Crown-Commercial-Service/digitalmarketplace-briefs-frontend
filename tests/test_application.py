import mock
from wtforms import ValidationError
from .helpers import BaseApplicationTest
from dmapiclient.errors import HTTPError


class TestApplication(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.find_direct_award_projects.return_value = {'meta': {'total': 1}}
        self.data_api_client.find_briefs.return_value = {'meta': {'total': 1}}
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_404(self):
        response = self.client.get('/buyers/not-found')
        assert 404 == response.status_code

    def test_503(self):
        self.data_api_client.find_direct_award_projects.side_effect = HTTPError('API is down')
        self.app.config['DEBUG'] = False

        res = self.client.get('/buyers')
        assert res.status_code == 503
        assert u"Sorry, we’re experiencing technical difficulties" in res.get_data(as_text=True)
        assert "Try again later." in res.get_data(as_text=True)

    def test_trailing_slashes(self):
        response = self.client.get('/buyers/')
        assert 301 == response.status_code
        assert "http://localhost/buyers" == response.location

    def test_header_xframeoptions_set_to_deny(self):
        res = self.client.get('/buyers')
        assert 200 == res.status_code
        assert 'DENY', res.headers['X-Frame-Options']

    @mock.patch('flask_wtf.csrf.validate_csrf', autospec=True)
    def test_csrf_handler_redirects_to_login(self, validate_csrf):
        self.login_as_buyer()

        with self.app.app_context():
            self.app.config['WTF_CSRF_ENABLED'] = True

            # This will raise a CSRFError for us when the form is validated
            validate_csrf.side_effect = ValidationError('The CSRF session token is missing.')

            res = self.client.post(
                '/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-outcomes/create',
                data={'anything': 'here'},
            )

            self.assert_flashes("Your session has expired. Please log in again.", expected_category="error")
            assert res.status_code == 302

            # POST requests will not preserve the request path on redirect
            assert res.location == 'http://localhost/user/login'
            assert validate_csrf.call_args_list == [mock.call(None)]
