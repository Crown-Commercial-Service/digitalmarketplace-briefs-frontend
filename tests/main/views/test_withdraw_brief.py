import mock
import pytest

from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ...helpers import BaseApplicationTest

from lxml import html


class TestWithdrawBriefSubmission(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.withdraw_brief.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_brief.return_value = BriefStub().single_result_response()
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        self.brief = BriefStub(
            user_id=123,
            framework_slug='digital-outcomes-and-specialists-4',
            lot_slug="digital-specialists",
            status='draft'
        ).response()

        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_withdraw_brief_warning_page_displays_correctly(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[LotStub(slug='digital-specialists', allows_brief=True).response()]
        ).single_result_response()
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug='digital-outcomes-and-specialists-4',
            status='live',
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw"
        )

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        self.assert_breadcrumbs(res, extra_breadcrumbs=[
            (
                'I need a thing to do a thing',
                '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234'
            ),
            (
                "Are you sure you want to withdraw these requirements?",
            )
        ])

        page_title = document.xpath('//h1')[0].text_content()
        title_caption = document.cssselect('span.govuk-caption-xl')[0].text_content()
        assert title_caption == self.brief.get('title')
        assert page_title == "Are you sure you want to withdraw these requirements?"

        assert document.xpath(
            '//form[@action="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw"]' # noqa
        )[0] is not None

        submit_button = document.cssselect('button[name="withdraw_confirmed"]')
        cancel_link = document.xpath("//a[normalize-space()='Cancel']")

        assert len(submit_button) == 1
        assert len(cancel_link) == 1

        assert cancel_link[0].attrib['href'] == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234" # noqa

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_withdraw_brief_submission(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[LotStub(slug='digital-specialists', allows_brief=True).response()]
        ).single_result_response()
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug='digital-outcomes-and-specialists-4',
            status='live',
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw",
            data={"withdraw_confirmed": True}
        )

        assert res.status_code == 302
        assert self.data_api_client.delete_brief.call_args_list == []
        assert res.location == "http://localhost{}".format(self.briefs_dashboard_url)
        self.assert_flashes(
            "You’ve withdrawn your requirements for ‘I need a thing to do a thing’",
            expected_category="success"
        )

    @pytest.mark.parametrize('framework_status', ['coming', 'open', 'pending', 'standstill'])
    def test_404_if_framework_is_not_live_or_expired(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[LotStub(slug='digital-specialists', allows_brief=True).response()]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw",
            data={"withdraw_confirmed": True}
        )
        assert res.status_code == 404
        assert not self.data_api_client.delete_brief.called

    @pytest.mark.parametrize('status', ['draft', 'closed', 'awarded', 'cancelled', 'unsuccessful', 'withdrawn'])
    def test_cannot_withdraw_non_live_brief(self, status):
        self.data_api_client.get_brief.return_value = BriefStub(status=status).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw",
            data={"withdraw_confirmed": True}
        )

        assert res.status_code == 404
        assert self.data_api_client.delete_brief.call_args_list == []

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(user_id=234, status='live').single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw",
            data={"withdraw_confirmed": True}
        )

        assert res.status_code == 404

    def test_404_if_brief_has_wrong_lot(self):
        self.data_api_client.get_brief.return_value = BriefStub(status='live').single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/withdraw",
            data={"withdraw_confirmed": True})

        assert res.status_code == 404
