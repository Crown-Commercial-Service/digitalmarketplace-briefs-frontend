# coding: utf-8
import mock

import pytest
from lxml import html
from dmtestutils.api_model_stubs import FrameworkStub, LotStub

from ...helpers import BaseApplicationTest


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
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists")
        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Find an individual specialist"

    @pytest.mark.parametrize(
        ('slug_suffix', 'lot_slug'),
        (
            ('', 'digital-outcomes'),
            ('', 'digital-specialists'),
            ('', 'user-research-participants'),
            ('-2', 'digital-outcomes'),
            ('-2', 'digital-specialists'),
            ('-2', 'user-research-participants'),
            ('-3', 'digital-outcomes'),
            ('-3', 'digital-specialists'),
            ('-3', 'user-research-participants'),
        )
    )
    def test_has_correct_link_to_supplier_csv(self, slug_suffix, lot_slug):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug=f'digital-outcomes-and-specialists{slug_suffix}',
            status='live',
            lots=[
                LotStub(slug=lot_slug, allows_brief=True).response(),
            ]
        ).single_result_response()
        res = self.client.get(
            f"/buyers/frameworks/digital-outcomes-and-specialists{slug_suffix}/requirements/{lot_slug}"
        )
        assert res.status_code == 200

        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath("//a[normalize-space()='Download list of suppliers.']")[0].attrib['href'] == (
            f"https://assets.digitalmarketplace.service.gov.uk/"
            f"digital-outcomes-and-specialists{slug_suffix}/communications/catalogues/{lot_slug}-suppliers.csv"
        )

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists")
        assert res.status_code == 404

    def test_404_if_framework_status_is_not_live(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='open',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()

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
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='user-research-studios').response(),
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/user-research-studios")
        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Find a user research lab"

    @pytest.mark.parametrize(('slug_suffix'), ('', '-2', '-3'))
    def test_has_correct_link_to_supplier_csv(self, slug_suffix):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug=f'digital-outcomes-and-specialists{slug_suffix}',
            status='live',
            lots=[
                LotStub(slug='user-research-studios', allows_brief=True).response(),
            ]
        ).single_result_response()
        res = self.client.get(
            f"/buyers/frameworks/digital-outcomes-and-specialists{slug_suffix}/requirements/user-research-studios"
        )
        assert res.status_code == 200

        document = html.fromstring(res.get_data(as_text=True))

        assert document.xpath("//a[normalize-space(text())='List of labs (CSV)']")[0].attrib['href'] == (
            f"https://assets.digitalmarketplace.service.gov.uk/digital-outcomes-and-specialists{slug_suffix}"
            f"/communications/catalogues/user-research-studios.csv"
        )

    def test_404_if_framework_status_is_not_live(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='open',
            lots=[
                LotStub(slug='user-research-studios').response(),
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/user-research-studios")
        assert res.status_code == 404
