import mock
import pytest
from lxml import html

from dmcontent.content_loader import ContentLoader
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ...helpers import BaseApplicationTest


class TestBriefSummaryPage(BaseApplicationTest):

    SIDE_LINKS_XPATH = '//div[@class="govuk-grid-column-one-third"]//a'
    INSTRUCTION_LINKS_XPATH = '//main//ul/li/a'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.requirement_task_list.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
        ).single_result_response()
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @staticmethod
    def _get_links(document, xpath, text_only=None):
        if text_only:
            return [e.text_content() for e in document.xpath(xpath)]
        return [
            (e.text_content(), e.get('href')) for e in document.xpath(xpath)
        ]

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_draft_brief_summary_page(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert (document.xpath('//h1')[0]).text_content().strip() == "I need a thing to do a thing"
        assert self._get_links(document, self.INSTRUCTION_LINKS_XPATH, text_only=True) == [
            'Title',
            'Specialist role',
            'Location',
            'Description of work',
            'Shortlist and evaluation process',
            'Set how long your requirements will be open for',
            'Describe question and answer session',
            'Preview your requirements',
            'Publish your requirements',
            'How to answer supplier questions',
            'How to shortlist suppliers',
            'How to evaluate suppliers',
            'How to award a contract',
            'Download the Digital Outcomes and Specialists 4 contract',
        ]

        assert "Awarded to " not in page_html
        assert self._get_links(document, self.SIDE_LINKS_XPATH) == [
            (
                "Delete draft requirements",
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/delete"  # noqa
            )
        ]

    @pytest.mark.parametrize(
        'status, banner_displayed',
        [
            ('draft', True),
            ('live', False), ('closed', False), ('awarded', False), ('cancelled', False), ('unsuccessful', False)
        ]
    )
    def test_brief_summary_with_delete_requested_displays_confirmation_banner_for_draft_briefs_only(
            self, status, banner_displayed
    ):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status=status,
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"  # noqa
        )

        assert res.status_code == 200

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_live_brief_summary_page_for_live_and_expired_framework(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="live",
        ).single_result_response()
        brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert (document.xpath('//h1')[0]).text_content().strip() == "I need a thing to do a thing"
        assert self._get_links(document, self.INSTRUCTION_LINKS_XPATH, text_only=True) == [
            'View question and answer dates',
            'View your published requirements',
            'Publish questions and answers',
            'How to answer supplier questions',
            'How to shortlist suppliers',
            'How to evaluate suppliers',
            'How to award a contract',
            'Download the Digital Outcomes and Specialists 4 contract',
        ]

        assert "Awarded to " not in page_html
        assert self._get_links(document, self.SIDE_LINKS_XPATH) == [
            (
                'Withdraw requirements',
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/withdraw"  # noqa
            )
        ]

    @pytest.mark.parametrize(
        'status, banner_displayed',
        [
            ('live', True),
            ('draft', False), ('closed', False), ('awarded', False), ('cancelled', False), ('unsuccessful', False)
        ]
    )
    def test_brief_summary_with_withdraw_requested_displays_confirmation_banner_for_live_briefs_only(
            self, status, banner_displayed
    ):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status=status,
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234?withdraw_requested=True"  # noqa
        )

        assert res.status_code == 200

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_closed_brief_summary_page_for_live_and_expired_framework(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="closed",
        ).single_result_response()
        brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert (document.xpath('//h1')[0]).text_content().strip() == "I need a thing to do a thing"
        assert self._get_links(document, self.INSTRUCTION_LINKS_XPATH, text_only=True) == [
            'View your published requirements',
            'View and shortlist suppliers',
            'How to shortlist suppliers',
            'How to evaluate suppliers',
            'How to award a contract',
            'Download the Digital Outcomes and Specialists 4 contract',
            'Let suppliers know the outcome'
        ]

        assert "Awarded to " not in page_html
        assert self._get_links(document, self.SIDE_LINKS_XPATH) == [
            (
                'Cancel requirements',
                '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/cancel'
            )
        ]

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    @pytest.mark.parametrize(
        'status,award_description',
        [('cancelled', 'the requirements were cancelled'), ('unsuccessful', 'no suitable suppliers applied')]
    )
    def test_show_cancelled_and_unsuccessful_brief_summary_page_for_live_and_expired_framework(
            self, status, award_description, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status=status,
        ).single_result_response()
        brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert (document.xpath('//h1')[0]).text_content().strip() == "I need a thing to do a thing"
        assert self._get_links(document, self.INSTRUCTION_LINKS_XPATH, text_only=True) == [
            'View your published requirements',
            'View suppliers who applied',
        ]
        assert "The contract was not awarded - {}.".format(award_description) in page_html

        assert "Awarded to " not in page_html
        assert self._get_links(document, self.SIDE_LINKS_XPATH) == []

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_awarded_brief_summary_page_for_live_and_expired_framework(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="awarded",
        ).single_result_response()
        brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        brief_json['briefs']['awardedBriefResponseId'] = 999
        self.data_api_client.get_brief.return_value = brief_json

        self.data_api_client.get_brief_response.return_value = {
            "briefResponses": {
                "awardDetails": {
                    "awardedContractStartDate": "2016-4-4",
                    "awardedContractValue": "100"
                },
                "id": 213,
                "status": "awarded",
                "supplierName": "100 Percent IT Ltd",
            }
        }

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200

        assert self.data_api_client.get_brief_response.call_args_list == [
            mock.call(999)
        ]

        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert (document.xpath('//h1')[0]).text_content().strip() == "I need a thing to do a thing"
        assert self._get_links(document, self.INSTRUCTION_LINKS_XPATH, text_only=True) == [
            'View your published requirements',
            'View suppliers who applied',
        ]
        assert "Awarded to 100 Percent IT Ltd" in page_html
        assert self._get_links(document, self.SIDE_LINKS_XPATH) == []

    def test_404_if_framework_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response(),
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 404

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            user_id=234,
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 404

    def test_404_if_brief_has_wrong_lot(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234"
        )

        assert res.status_code == 404

    @mock.patch("app.main.views.requirement_task_list.content_loader", autospec=True)
    def test_links_to_sections_go_to_the_correct_pages_whether_they_be_sections_or_questions(self, content_loader):  # noqa
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 200

        document = html.fromstring(res.get_data(as_text=True))
        section_steps = document.cssselect("ol.instruction-list")
        section_1_link = section_steps[0].xpath('li//a[contains(text(), "Section 1")]')
        section_2_link = section_steps[0].xpath('li//a[contains(text(), "Section 2")]')
        section_4_link = section_steps[0].xpath('li//a[contains(text(), "Section 4")]')

        # section with multiple questions
        assert section_1_link[0].get('href').strip() == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1'
        # section with single question
        assert section_2_link[0].get('href').strip() == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/edit/section-2/required2'  # noqa
        # section with single question and a description
        assert section_4_link[0].get('href').strip() == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-4'
