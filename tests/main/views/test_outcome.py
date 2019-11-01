# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmapiclient import HTTPError
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub
import mock
from lxml import html
import pytest


class TestAwardBrief(BaseApplicationTest):
    brief_responses = {
        "briefResponses": [
            {"id": 23, "supplierName": "Dobbins"},
            {"id": 4444, "supplierName": "Cobbins"},
            {"id": 2, "supplierName": "Aobbins"},
            {"id": 90, "supplierName": "Bobbins"},
        ]
    }
    url = "/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/{brief_id}/award-contract"  # noqa

    def setup_method(self, method):
        super(TestAwardBrief, self).setup_method(method)

        self.data_api_client_patch = mock.patch('app.main.views.outcome.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response(),
            ]
        ).single_result_response()

        brief_stub = BriefStub(
            framework_slug="digital-outcomes-and-specialists-2", lot_slug="digital-outcomes", status='closed'
        ).single_result_response()
        self.data_api_client.get_brief.return_value = brief_stub

        self.data_api_client.find_brief_responses.return_value = self.brief_responses

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super(TestAwardBrief, self).teardown_method(method)

    def test_award_brief_200s_with_correct_default_content(self):
        self.login_as_buyer()

        res = self.client.get(self.url.format(brief_id=1234))

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        self.assert_breadcrumbs(res, extra_breadcrumbs=[
            (
                'I need a thing to do a thing',
                '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234'
            )
        ])

        page_title = self._strip_whitespace(document.xpath('//h1')[0].text_content())
        assert page_title == "WhowontheIneedathingtodoathingcontract?"

        submit_button = document.xpath(
            '//button[normalize-space(string())=$t]',
            t="Save and continue",
        )
        assert len(submit_button) == 1

        # No options should be selected
        labels = document.xpath('//label[@class="selection-button selection-button-radio"]/@class')
        for label_class in labels:
            assert "selected" not in label_class

    def test_award_brief_get_lists_suppliers_who_applied_for_this_brief_alphabetically(self):
        self.login_as_buyer()

        res = self.client.get(self.url.format(brief_id=1234))

        assert self.data_api_client.find_brief_responses.call_args == mock.call(
            1234, status="submitted,pending-awarded"
        )

        document = html.fromstring(res.get_data(as_text=True))
        for i, brief_response in enumerate([(2, 'Aobbins'), (90, 'Bobbins'), (4444, 'Cobbins'), (23, 'Dobbins')]):
            input_id = document.xpath('//input[@id="input-brief_response-{}"]/@value'.format(i + 1))[0]
            assert int(input_id) == brief_response[0]
            label = document.xpath('//label[@for="input-brief_response-{}"]'.format(i + 1))[0]
            assert self._strip_whitespace(label.text_content()) == brief_response[1]

    def test_award_brief_get_populates_form_with_a_previously_chosen_brief_response(self):
        self.data_api_client.find_brief_responses.return_value = {
            "briefResponses": [
                {"id": 23, "supplierName": "Dobbins"},
                {"id": 4444, "supplierName": "Cobbins"},
                {"id": 2, "supplierName": "Aobbins"},
                {"id": 90, "supplierName": "Bobbins", "awardDetails": {"pending": True}},
            ]
        }

        self.login_as_buyer()

        res = self.client.get(self.url.format(brief_id=1234))
        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        selected_label_class = document.xpath('//label[@for="input-brief_response-2"]/@class')[0]
        assert "selected" in selected_label_class

        assert self.data_api_client.find_brief_responses.call_args == mock.call(
            1234, status="submitted,pending-awarded"
        )

    def test_award_brief_get_redirects_to_login_if_not_authenticated(self):
        target_url = self.url.format(brief_id=1234)
        res = self.client.get(target_url)
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login?next={}'.format(target_url.replace('/', '%2F'))

    @pytest.mark.parametrize('status', ['live', 'draft', 'withdrawn', 'awarded', 'cancelled', 'unsuccessful'])
    def test_award_brief_get_returns_404_if_brief_not_closed(self, status):
        self.data_api_client.get_brief.return_value['briefs']['status'] = status
        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234))
        assert res.status_code == 404

    @mock.patch('app.main.views.outcome.is_brief_correct')
    def test_award_brief_get_returns_404_if_brief_not_correct(self, is_brief_correct):
        is_brief_correct.return_value = False

        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234))
        assert res.status_code == 404

    def test_award_brief_redirects_to_brief_responses_page_if_no_suppliers_applied(self):
        self.data_api_client.find_brief_responses.return_value = {"briefResponses": []}
        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234))
        assert res.status_code == 302
        assert "/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234/responses" in res.location  # noqa

    def test_award_brief_post_raises_400_if_required_fields_not_filled(self):
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=1234), data={})
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 400

        validation_message = document.xpath('//span[@class="validation-message"]')[0].text_content()
        assert validation_message.strip() == "You need to answer this question."

        error_span = document.xpath('//span[@id="error-brief_response"]')[0]
        assert self._strip_whitespace(error_span.text_content()) == "Youneedtoanswerthisquestion."

    def test_award_brief_post_raises_400_if_form_not_valid(self):
        self.login_as_buyer()
        # Not a valid choice on the AwardedBriefResponseForm list
        res = self.client.post(self.url.format(brief_id=1234), data={'brief_response': 999})
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 400

        validation_message = document.xpath('//span[@class="validation-message"]')[0].text_content()
        assert validation_message.strip() == "Not a valid choice"

        error_span = document.xpath('//span[@id="error-brief_response"]')[0]
        assert self._strip_whitespace(error_span.text_content()) == "Notavalidchoice"

    def test_award_brief_post_valid_form_calls_api_and_redirects_to_next_question(self):
        self.data_api_client.update_brief_award_brief_response.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='closed',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response()
            ]
        )

        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=1234), data={'brief_response': 2})

        assert self.data_api_client.update_brief_award_brief_response.call_args == mock.call(
            u'1234', 2, "buyer@email.com"
        )
        assert res.status_code == 302
        assert "/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234/award/2/contract-details" in res.location  # noqa

    def test_award_brief_post_raises_500_on_api_error_and_displays_generic_error_message(self):
        self.data_api_client.update_brief_award_brief_response.side_effect = HTTPError(
            mock.Mock(status_code=500),
            {"title": "BriefResponse cannot be awarded for this Brief"}
        )
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=1234), data={'brief_response': 2})
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 500
        error_span = document.xpath('//h1')[0]
        assert self._strip_whitespace(error_span.text_content()) == "Sorry,we’reexperiencingtechnicaldifficulties"


class TestAwardBriefDetails(BaseApplicationTest):
    url = "/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/{brief_id}/award/{brief_response_id}/contract-details"  # noqa

    def setup_method(self, method):
        super(TestAwardBriefDetails, self).setup_method(method)

        self.data_api_client_patch = mock.patch('app.main.views.outcome.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response(),
            ]
        ).single_result_response()

        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug='digital-outcomes-and-specialists-2', lot_slug="digital-outcomes", status='closed'
        ).single_result_response()
        self.data_api_client.get_brief_response.return_value = {
            "briefResponses": {
                "id": 5678,
                "briefId": 1234,
                "status": "pending-awarded",
                "supplierName": "BananaCorp",
                "awardDetails": {"pending": True}
            }
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super(TestAwardBriefDetails, self).teardown_method(method)

    def _setup_api_error_response(self, error_json):
        self.data_api_client.update_brief_award_details.side_effect = HTTPError(mock.Mock(status_code=400), error_json)

    def test_award_brief_details_200s_with_correct_default_content(self):
        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234, brief_response_id=5678))

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        self.assert_breadcrumbs(res, extra_breadcrumbs=[
            (
                'I need a thing to do a thing',
                '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234'
            )
        ])

        page_title = self._strip_whitespace(document.xpath('//h1')[0].text_content())
        assert page_title == "TellusaboutyourcontractwithBananaCorp"

        submit_button = document.xpath(
            '//button[@type="submit"][normalize-space(string())=$t]',
            t="Update requirements",
        )
        assert len(submit_button) == 1

        secondary_link_text = document.xpath('//div[@class="secondary-action-link"]//a[1]')[0]
        assert secondary_link_text.text_content() == "Previous page"

        secondary_link = document.xpath('//div[@class="secondary-action-link"]//a[1]/@href')[0]
        assert secondary_link == \
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234/award-contract'

    def test_award_brief_details_post_valid_form_calls_api_and_redirects(self):
        self.data_api_client.update_brief_award_details.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='awarded',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response()
            ]
        ).single_result_response()
        self.login_as_buyer()
        res = self.client.post(
            self.url.format(brief_id=1234, brief_response_id=5678),
            data={
                "awardedContractStartDate-day": "31",
                "awardedContractStartDate-month": "12",
                "awardedContractStartDate-year": "2020",
                "awardedContractValue": "88.84"
            }
        )

        assert self.data_api_client.update_brief_award_details.call_args == mock.call(
            '1234', '5678',
            {'awardedContractStartDate': "2020-12-31", "awardedContractValue": "88.84"},
            updated_by="buyer@email.com"
        )
        assert res.status_code == 302
        assert res.location == "http://localhost{}".format(self.briefs_dashboard_url)
        self.assert_flashes("You’ve updated ‘I need a thing to do a thing’", "message")

    @mock.patch('app.main.views.outcome.is_brief_correct')
    def test_award_brief_details_raises_400_if_brief_not_correct(self, is_brief_correct):
        is_brief_correct.return_value = False
        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234, brief_response_id=5678))
        assert res.status_code == 404

    @pytest.mark.parametrize('status', ['awarded', 'submitted', 'draft'])
    def test_award_brief_details_raises_404_if_brief_response_not_pending(self, status):
        self.data_api_client.get_brief_response.return_value["briefResponses"]["status"] = status

        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234, brief_response_id=5678))
        assert res.status_code == 404

    def test_award_brief_details_raises_404_if_brief_response_not_related_to_brief(self):
        """Fake brief_response, as if the user has changed the brief_response.id in the url."""
        self.data_api_client.get_brief_response.return_value['briefResponses']['briefId'] = 9

        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234, brief_response_id=99))
        assert res.status_code == 404

    def test_award_brief_details_raises_404_if_brief_not_related_to_brief_response(self):
        """Fake brief, as if the user has changed the brief_id in the url."""
        self.data_api_client.get_brief.return_value['briefs']['id'] = 9

        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=9, brief_response_id=5678))
        assert res.status_code == 404

    def _assert_masthead(self, document):
        masthead_error_links = document.xpath('//a[@class="validation-masthead-link"]')
        assert masthead_error_links[0].text_content() == "What's the start date?"
        assert masthead_error_links[1].text_content() == "What's the value?"

    def test_award_brief_details_post_raises_400_if_required_fields_not_filled(self):
        self._setup_api_error_response({
            "awardedContractValue": "answer_required",
            "awardedContractStartDate": "answer_required"
        })
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=1234, brief_response_id=5678), data={})
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 400
        self._assert_masthead(document)
        error_spans = document.xpath('//span[@class="validation-message"]')
        assert self._strip_whitespace(error_spans[0].text_content()) == "Youneedtoanswerthisquestion."
        assert self._strip_whitespace(error_spans[1].text_content()) == "Youneedtoanswerthisquestion."

    def test_award_brief_details_post_raises_400_and_displays_error_messages_and_prefills_fields_if_invalid_data(self):
        self._setup_api_error_response({
            "awardedContractStartDate": "invalid_format",
            "awardedContractValue": "not_money_format"
        })
        self.login_as_buyer()

        res = self.client.post(
            self.url.format(brief_id=1234, brief_response_id=5678),
            data={
                "awardedContractValue": "incorrect",
                "awardedContractStartDate-day": "x",
                "awardedContractStartDate-month": "y",
                "awardedContractStartDate-year": "z"
            }
        )

        assert res.status_code == 400
        document = html.fromstring(res.get_data(as_text=True))

        self._assert_masthead(document)

        # Individual error messages
        error_spans = document.xpath('//span[@class="validation-message"]')
        assert self._strip_whitespace(error_spans[0].text_content()) == "Youranswermustbeavaliddate."
        assert self._strip_whitespace(error_spans[1].text_content()) == \
            "Enteryourvalueinpoundsandpenceusingnumbersanddecimalsonly,forexample9900.05for9900poundsand5pence."

        # Prefilled form input
        assert document.xpath('//input[@id="input-awardedContractValue"]/@value')[0] == "incorrect"
        assert document.xpath('//input[@id="input-awardedContractStartDate-day"]/@value')[0] == "x"
        assert document.xpath('//input[@id="input-awardedContractStartDate-month"]/@value')[0] == "y"
        assert document.xpath('//input[@id="input-awardedContractStartDate-year"]/@value')[0] == "z"


class TestCancelBrief(BaseApplicationTest):
    url = '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/{brief_id}/cancel'

    def setup_method(self, method):
        super(TestCancelBrief, self).setup_method(method)

        self.data_api_client_patch = mock.patch('app.main.views.outcome.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response(),
            ]
        ).single_result_response()
        self.brief = BriefStub(
            user_id=123,
            framework_slug='digital-outcomes-and-specialists-2',
            lot_slug="digital-outcomes",
            status='closed'
        ).response()
        self.data_api_client.get_brief.return_value = {"briefs": self.brief}
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super(TestCancelBrief, self).teardown_method(method)

    def test_cancel_brief_form_displays_default_title_correctly_when_accessed_through_cancel_url(self):
        """
        This form has a dynamic title dependent on the url it is accessed through.

        This test checks for the default "Why do you need to cancel <brief_name>? title when accessed
        through the '/cancel' url".
        """
        self.login_as_buyer()
        res = self.client.get(self.url.format(brief_id=1234))

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        self.assert_breadcrumbs(res, extra_breadcrumbs=[
            (
                'I need a thing to do a thing',
                '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234'
            )
        ])

        page_title = document.xpath('//h1')[0].text_content()
        assert "Why do you need to cancel {}?".format(self.brief.get('title')) in page_title

        submit_button = document.xpath(
            '//button[normalize-space(string())=$t]',
            t="Update requirements",
        )
        assert len(submit_button) == 1

        expected_previous_page_link_text = 'Previous page'
        expected_previous_page_link_url = (
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234'
        )

        assert (
            document.xpath("//a[text()='{}']/@href".format(expected_previous_page_link_text))[0] ==
            expected_previous_page_link_url
        )

    def test_cancel_form_post_action_is_correct_when_accessed_from_cancel_url(self):
        url = (
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/'
            'digital-outcomes/{brief_id}/cancel'
        )

        self.login_as_buyer()
        res = self.client.get(url.format(brief_id=1234))
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//form[@action="{}"]'.format(url.format(brief_id=1234)))[0] is not None

        res = self.client.post(url.format(brief_id=1234))
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//form[@action="{}"]'.format(url.format(brief_id=1234)))[0] is not None

    def test_cancel_form_displays_correctly_accessed_from_award_flow_url(self):
        url = (
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/'
            'digital-outcomes/{brief_id}/cancel-award'
        )

        self.login_as_buyer()
        res = self.client.get(url.format(brief_id=1234))
        assert res.status_code == 200

        document = html.fromstring(res.get_data(as_text=True))
        page_title = document.xpath('//h1')[0].text_content()
        assert "Why didn’t you award a contract for {}?".format(self.brief.get('title')) in page_title

        submit_button = document.xpath(
            '//button[normalize-space(string())=$t]',
            t="Update requirements",
        )
        assert len(submit_button) == 1

        expected_previous_page_link_text = 'Previous page'
        expected_previous_page_link_url = (
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/1234/award'
        )

        assert (
            document.xpath("//a[text()='{}']/@href".format(expected_previous_page_link_text))[0] ==
            expected_previous_page_link_url
        )

    def test_cancel_form_post_action_is_correct_when_accessed_from_award_flow_url(self):
        url = (
            '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/'
            'digital-outcomes/{brief_id}/cancel-award'
        )

        self.login_as_buyer()
        res = self.client.get(url.format(brief_id=1234))
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//form[@action="{}"]'.format(url.format(brief_id=1234)))[0] is not None

        res = self.client.post(url.format(brief_id=1234))
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//form[@action="{}"]'.format(url.format(brief_id=1234)))[0] is not None

    def test_404_if_user_is_not_brief_owner(self):
        self.data_api_client.get_brief.return_value['briefs']['users'][0]['id'] = 234

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        assert res.status_code == 404

    @pytest.mark.parametrize('status', ['withdrawn', 'draft', 'live', 'cancelled', 'unsuccessful', 'awarded'])
    def test_404_if_brief_not_closed(self, status):
        self.data_api_client.get_brief.return_value['briefs']['status'] = status

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        assert res.status_code == 404

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_200_for_acceptable_framework_statuses(self, framework_status):
        self.data_api_client.get_framework.return_value['frameworks']['status'] = framework_status

        res = self.client.get(self.url.format(brief_id=123))

        assert res.status_code == 200

    def test_that_no_option_chosen_triggers_error(self):
        res = self.client.post(self.url.format(brief_id=123))

        document = html.fromstring(res.get_data(as_text=True))
        validation_message = document.xpath('//span[@class="validation-message"]')[0].text_content()

        assert res.status_code == 400
        assert "You need to answer this question." in validation_message

    def test_that_no_option_chosen_does_not_trigger_update(self):
        res = self.client.post(self.url.format(brief_id=123))

        assert res.status_code == 400
        self.data_api_client.cancel_brief.assert_not_called()

    def test_cancel_triggers_cancel_brief(self):
        res = self.client.post(
            self.url.format(brief_id=123), data={'cancel_reason': 'cancel'}
        )

        assert res.status_code == 302
        self.data_api_client.cancel_brief.assert_called_once_with('123', user='buyer@email.com')

    def test_unsuccessful_triggers_cancel_brief(self):
        res = self.client.post(
            self.url.format(brief_id=123), data={'cancel_reason': 'unsuccessful'}
        )

        assert res.status_code == 302
        self.data_api_client.update_brief_as_unsuccessful.assert_called_once_with('123', user='buyer@email.com')

    @pytest.mark.parametrize('status', ['withdrawn', 'draft', 'live', 'closed', 'awarded'])
    def test_400_if_incorrect_status_supplied(self, status):
        res = self.client.post(
            self.url.format(brief_id=123), data={'cancel_reason': status}
        )

        assert res.status_code == 400
        assert "Not a valid choice" in res.get_data(as_text=True)

    @pytest.mark.parametrize('status', ['withdrawn', 'draft', 'live', 'closed', 'awarded'])
    def test_update_methods_not_called_if_incorrect_status_supplied(self, status):
        res = self.client.post(
            self.url.format(brief_id=123), data={'cancel_reason': status}
        )

        assert res.status_code == 400
        self.data_api_client.update_brief_as_unsuccessful.assert_not_called()
        self.data_api_client.cancel_brief.assert_not_called()

    @pytest.mark.parametrize('status', ['cancel', 'unsuccessful'])
    def test_redirect_and_flash_on_successful_status_change(self, status):
        res = self.client.post(
            self.url.format(brief_id=123), data={'cancel_reason': status}
        )

        redirect_text = html.fromstring(res.get_data(as_text=True)).text_content().strip()
        expected_url = '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/123'

        assert res.status_code == 302
        assert expected_url in redirect_text
        self.assert_flashes("You’ve updated ‘I need a thing to do a thing’", "message")


class TestAwardOrCancelBrief(BaseApplicationTest):
    url = '/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/digital-outcomes/{brief_id}/award'

    def setup_method(self, method):
        super(TestAwardOrCancelBrief, self).setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.outcome.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-2',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response(),
            ]
        ).single_result_response()
        self.brief = BriefStub(
            user_id=123,
            framework_slug='digital-outcomes-and-specialists-2',
            lot_slug="digital-outcomes",
            status='closed'
        ).response()

        self.data_api_client.get_brief.return_value = {"briefs": self.brief}
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super(TestAwardOrCancelBrief, self).teardown_method(method)

    def test_404_if_user_is_not_brief_owner(self):
        self.data_api_client.get_brief.return_value['briefs']['users'][0]['id'] = 234

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        assert res.status_code == 404

    @pytest.mark.parametrize('status', ['withdrawn', 'draft', 'live'])
    def test_404_if_brief_not_closed_and_award_flow_not_yet_completed(self, status):
        self.data_api_client.get_brief.return_value['briefs']['status'] = status

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        assert res.status_code == 404

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_200_for_acceptable_framework_statuses(self, framework_status):
        self.data_api_client.get_framework.return_value['frameworks']['status'] = framework_status

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        assert res.status_code == 200

    @pytest.mark.parametrize('status', ['awarded', 'cancelled', 'unsuccessful'])
    def test_200_with_error_message_if_award_flow_already_completed(self, status):
        self.data_api_client.get_brief.return_value['briefs']['status'] = status

        res = self.client.get(self.url.format(brief_id=self.brief["id"]))

        document = html.fromstring(res.get_data(as_text=True))
        page_title = self._strip_whitespace(document.xpath('//h1')[0].text_content())
        view_outcome_link = document.xpath('//div[@class="single-question-page"]//a')[0].text_content()

        assert res.status_code == 200
        assert page_title == "RequirementsalreadyupdatedforIneedathingtodoathing"
        assert view_outcome_link == "View the outcome of the requirements"

    def test_that_no_option_chosen_triggers_error(self):
        res = self.client.post(self.url.format(brief_id=123))

        document = html.fromstring(res.get_data(as_text=True))
        validation_message = document.xpath('//span[@class="validation-message"]')[0].text_content()

        assert res.status_code == 400
        assert "You need to answer this question." in validation_message
        assert self.data_api_client.cancel_brief.called is False

    def test_yes_redirects_to_award_form_page(self):
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=self.brief['id']), data={'award_or_cancel_decision': 'yes'})

        expected_url = (
            'http://localhost/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/'
            'digital-outcomes/{}/award-contract'
        ).format(self.brief['id'])

        assert res.status_code == 302
        assert res.location == expected_url

    def test_no_redirects_to_cancel_or_award_form_page(self):
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=self.brief['id']), data={'award_or_cancel_decision': 'no'})

        expected_url = (
            'http://localhost/buyers/frameworks/digital-outcomes-and-specialists-2/requirements/'
            'digital-outcomes/{}/cancel-award'
        ).format(self.brief['id'])

        assert res.status_code == 302
        assert res.location == expected_url

    def test_back_redirects_to_buyer_dos_requiremnents_list(self):
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=self.brief['id']), data={'award_or_cancel_decision': 'back'})

        expected_url = 'http://localhost/buyers/requirements/digital-outcomes-and-specialists'

        assert res.status_code == 302
        assert res.location == expected_url

    def test_back_causes_flash_message(self):
        self.login_as_buyer()
        self.client.post(self.url.format(brief_id=self.brief['id']), data={'award_or_cancel_decision': 'back'})

        self.assert_flashes("You’ve updated ‘I need a thing to do a thing’", "message")

    def test_random_post_data_triggers_invalid_choice(self):
        self.login_as_buyer()
        res = self.client.post(self.url.format(brief_id=self.brief['id']), data={'award_or_cancel_decision': 'foo'})

        document = html.fromstring(res.get_data(as_text=True))
        validation_message = document.xpath('//span[@class="validation-message"]')[0].text_content()

        assert res.status_code == 400
        assert "Not a valid choice" in validation_message
