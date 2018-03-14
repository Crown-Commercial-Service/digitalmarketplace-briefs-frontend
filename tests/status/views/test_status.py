import json
from ...helpers import BaseApplicationTest

import mock


class TestStatus(BaseApplicationTest):

    def setup_method(self, method):
        super(TestStatus, self).setup_method(method)

        self._data_api_client_patch = mock.patch('app.status.views.data_api_client', autospec=True)
        self._data_api_client = self._data_api_client_patch.start()

    def teardown_method(self, method):
        self._data_api_client_patch.stop()

    def test_should_return_200_from_elb_status_check(self):
        status_response = self.client.get('/buyers/_status?ignore-dependencies')
        assert status_response.status_code == 200
        assert self._data_api_client.called is False

    def test_status_ok(self):
        self._data_api_client.get_status.return_value = {
            'status': 'ok'
        }

        status_response = self.client.get('/buyers/_status')
        assert status_response.status_code == 200

        json_data = json.loads(status_response.get_data().decode('utf-8'))
        assert "{}".format(json_data['api_status']['status']) == "ok"

    def test_status_error_in_one_upstream_api(self):
        self._data_api_client.get_status.return_value = {
            'status': 'error',
            'app_version': None,
            'message': 'Cannot connect to database'
        }

        response = self.client.get('/buyers/_status')
        assert response.status_code == 500

        json_data = json.loads(response.get_data().decode('utf-8'))

        assert "{}".format(json_data['status']) == "error"
        assert "{}".format(json_data['api_status']['status']) == "error"

    def test_status_no_response_in_one_upstream_api(self):
        self._data_api_client.get_status.return_value = None

        response = self.client.get('/buyers/_status')
        assert response.status_code == 500

        json_data = json.loads(response.get_data().decode('utf-8'))

        assert "{}".format(json_data['status']) == "error"
        assert json_data.get('api_status') == {'status': 'n/a'}
