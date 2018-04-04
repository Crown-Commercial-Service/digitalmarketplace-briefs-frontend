# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmapiclient import api_stubs
import mock
from lxml import html


class TestStartBriefInfoPage(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            'app.main.views.digital_outcomes_and_specialists.data_api_client', autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_show_start_brief_info_page(self):
        self.data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=True),
            ]
        )

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists")
        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Find an individual specialist"

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=False)
            ]
        )

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists")
        assert res.status_code == 404

    def test_404_if_framework_status_is_not_live(self):
        self.data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='open',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=True),
            ]
        )

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists")
        assert res.status_code == 404


class TestStartStudiosInfoPage(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            'app.main.views.digital_outcomes_and_specialists.data_api_client', autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_show_start_studios_info_page(self):
        self.data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='user-research-studios'),
            ]
        )

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/user-research-studios")
        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Find a user research lab"

    def test_404_if_framework_status_is_not_live(self):
        self.data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='open',
            lots=[
                api_stubs.lot(slug='user-research-studios'),
            ]
        )

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/user-research-studios")
        assert res.status_code == 404
