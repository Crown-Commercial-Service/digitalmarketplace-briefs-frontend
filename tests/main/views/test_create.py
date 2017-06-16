import mock
from flask import session
from dmutils.email.exceptions import EmailError
from dmapiclient.audit import AuditTypes
from ...helpers import BaseApplicationTest

USER_CREATION_EMAIL_ERROR = "Failed to send user creation email."


class TestBuyersCreation(BaseApplicationTest):
    def test_should_get_create_buyer_form_ok(self):
        res = self.client.get('/buyers/create')
        assert res.status_code == 200
        assert 'Create a buyer account' in res.get_data(as_text=True)

    @mock.patch('app.main.views.create.send_email')
    @mock.patch('app.main.views.create.data_api_client')
    def test_should_be_able_to_submit_valid_email_address(self, data_api_client, send_email):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'valid@test.gov.uk'},
            follow_redirects=False
        )
        assert res.status_code == 302
        assert res.location == 'http://localhost/create-your-account-complete'

    @mock.patch('app.main.views.create.send_email')
    @mock.patch('app.main.views.create.data_api_client')
    def test_creating_account_doesnt_affect_csrf_token(self, data_api_client, send_email):
        with self.client as c:
            res = c.get(
                '/buyers/create',
            )
            original_csrf_token = session.get("csrf_token")
            assert original_csrf_token
        with self.client as c2:
            res2 = c2.post(
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

    @mock.patch('app.main.views.create.data_api_client')
    def test_should_show_error_page_for_unrecognised_email_domain(self, data_api_client):
        data_api_client.is_email_address_with_valid_buyer_domain.return_value = False
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'kev@ymail.com'},
            follow_redirects=True
        )
        assert res.status_code == 400
        data = res.get_data(as_text=True)
        assert "You must use a public sector email address" in data
        assert "The email you used doesn't belong to a recognised public sector domain." in data

    @mock.patch('app.main.views.create.data_api_client')
    @mock.patch('app.main.views.create.send_email')
    def test_should_503_if_email_fails_to_send(self, send_email, data_api_client):
        data_api_client.is_email_address_with_valid_buyer_domain.return_value = True
        send_email.side_effect = EmailError("Arrrgh")
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'valid@test.gov.uk'},
            follow_redirects=True
        )
        assert res.status_code == 503
        assert USER_CREATION_EMAIL_ERROR in res.get_data(as_text=True)

    @mock.patch('app.main.views.create.send_email')
    @mock.patch('app.main.views.create.data_api_client')
    def test_should_create_audit_event_when_email_sent(self, data_api_client, send_email):
        res = self.client.post(
            '/buyers/create',
            data={'email_address': 'valid@test.gov.uk'},
            follow_redirects=False
        )
        assert res.status_code == 302
        data_api_client.create_audit_event.assert_called_with(audit_type=AuditTypes.invite_user,
                                                              data={'invitedEmail': 'valid@test.gov.uk'})
