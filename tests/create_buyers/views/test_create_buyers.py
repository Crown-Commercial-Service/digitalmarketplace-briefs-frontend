import mock
from flask import session, current_app
from dmapiclient.audit import AuditTypes
from ...helpers import BaseApplicationTest

USER_CREATION_EMAIL_ERROR = "Failed to send user creation email."


class TestBuyersCreation(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.create_buyer.views.create_buyer.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_get_create_buyer_form_ok(self):
        res = self.client.get('/buyers/create')
        assert res.status_code == 200
        assert 'Create a buyer account' in res.get_data(as_text=True)

    @mock.patch('app.create_buyer.views.create_buyer.send_user_account_email')
    def test_should_be_able_to_submit_valid_email_address(self, send_user_account_email):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'valid@test.gov.uk'},
            follow_redirects=False
        )
        assert res.status_code == 302
        assert res.location == 'http://localhost/buyers/create-your-account-complete'

    def test_create_your_account_complete_page(self):
        res = self.client.get(
            '/buyers/create-your-account-complete',
            follow_redirects=False
        )
        assert res.status_code == 200

    @mock.patch('app.create_buyer.views.create_buyer.send_user_account_email')
    def test_creating_account_doesnt_affect_csrf_token(self, send_user_account_email):
        with self.client as c:
            c.get(
                '/buyers/create',
            )
            original_csrf_token = session.get("csrf_token")
            assert original_csrf_token
        with self.client as c2:
            c2.post(
                '/buyers/create',
                data={'email_address': 'definitely.definitely.definitely.valid@test.gov.uk'},
                follow_redirects=False
            )
            assert session.get("csrf_token") == original_csrf_token

    def test_should_raise_validation_error_for_invalid_email_address(self):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'not-an-email-address'},
            follow_redirects=True
        )
        assert res.status_code == 400
        data = res.get_data(as_text=True)
        assert 'Create a buyer account' in data
        assert 'You must provide a valid email address' in data

    def test_should_raise_validation_error_for_email_address_with_two_at_symbols(self):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'not-an@email@gov.uk'},
            follow_redirects=True
        )
        assert res.status_code == 400
        data = res.get_data(as_text=True)
        assert 'Create a buyer account' in data
        assert 'You must provide a valid email address' in data

    def test_should_raise_validation_error_for_empty_email_address(self):
        res = self.client.post(
            '/buyers/create',
            data={},
            follow_redirects=True
        )
        assert res.status_code == 400
        data = res.get_data(as_text=True)
        assert 'Create a buyer account' in data
        assert 'You must provide an email address' in data

    def test_should_show_error_page_for_unrecognised_email_domain(self):
        self.data_api_client.is_email_address_with_valid_buyer_domain.return_value = False
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'kev@ymail.com'},
            follow_redirects=True
        )
        assert res.status_code == 400
        data = res.get_data(as_text=True)
        assert "You must use a public sector email address" in data
        assert "The email you used doesn't belong to a recognised public sector domain." in data

    @mock.patch('app.create_buyer.views.create_buyer.send_user_account_email')
    def test_should_send_mail_with_correct_params(self, send_user_account_email):
        with self.app.app_context():

            res = self.client.post(
                '/buyers/create',
                data={'email_address': 'valid@test.gov.uk'},
                follow_redirects=False
            )

            send_user_account_email.assert_called_once_with(
                'buyer',
                'valid@test.gov.uk',
                current_app.config['NOTIFY_TEMPLATES']['create_user_account']
            )

            assert res.status_code == 302
            assert res.location == 'http://localhost/buyers/create-your-account-complete'

    @mock.patch('dmutils.email.user_account_email.DMNotifyClient')
    def test_email_address_is_correctly_stored_in_session(self, DMNotifyClient):
        with self.client as c:
            c.post(
                '/buyers/create',
                data={'email_address': 'valid@test.gov.uk'},
                follow_redirects=False
            )

            assert session.get('email_sent_to') == 'valid@test.gov.uk'

    @mock.patch('app.create_buyer.views.create_buyer.send_user_account_email')
    def test_should_create_audit_event_when_email_sent(self, send_user_account_email):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'valid@test.gov.uk'},
            follow_redirects=False
        )
        assert res.status_code == 302
        self.data_api_client.create_audit_event.assert_called_with(
            audit_type=AuditTypes.invite_user,
            data={'invitedEmail': 'valid@test.gov.uk'}
        )
