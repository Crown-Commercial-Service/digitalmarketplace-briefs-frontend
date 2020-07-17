import mock
import pytest
from freezegun import freeze_time
from lxml import html

from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ....helpers import BaseApplicationTest


class TestPreviewBrief(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.publish.data_api_client", autospec=True
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
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def _setup_brief(self, brief_status="draft", **stub_kwargs):
        brief_json = BriefStub(
            status=brief_status,
            framework_slug='digital-outcomes-and-specialists-4',
            **stub_kwargs
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'backgroundInformation': 'test background info',
            'contractLength': 'A very long time',
            'culturalFitCriteria': ['CULTURAL', 'FIT'],
            'culturalWeighting': 10,
            'essentialRequirements': 'Everything',
            'evaluationType': ['test evaluation type'],
            'existingTeam': 'team team team',
            'importantDates': 'Near future',
            'numberOfSuppliers': 5,
            'location': 'somewhere',
            'organisation': 'test organisation',
            'priceWeighting': 80,
            'specialistRole': 'communicationsManager',
            'specialistWork': 'work work work',
            'startDate': 'startDate',
            'summary': 'blah',
            'technicalWeighting': 10,
            'workingArrangements': 'arrangements',
            'workplaceAddress': 'address',
            'requirementsLength': '1 week'
        })
        return brief_json

    @pytest.mark.parametrize('framework_status', ['coming', 'open', 'pending', 'standstill', 'expired'])
    def test_preview_page_404s_if_framework_status_is_not_live(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")
        assert res.status_code == 404

    @pytest.mark.parametrize('framework_status', ['coming', 'open', 'pending', 'standstill', 'expired'])
    def test_preview_source_page_404s_if_framework_status_is_not_live(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.status_code == 404

    @pytest.mark.parametrize('brief_status', ['live', 'awarded', 'cancelled', 'closed', 'unsuccessful', 'withdrawn'])
    def test_preview_page_404s_if_brief_is_not_draft(self, brief_status):
        self.data_api_client.get_brief.return_value = self._setup_brief(brief_status=brief_status)

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")
        assert res.status_code == 404

    @pytest.mark.parametrize('brief_status', ['live', 'awarded', 'cancelled', 'closed', 'unsuccessful', 'withdrawn'])
    def test_preview_source_page_404s_if_brief_is_not_draft(self, brief_status):
        self.data_api_client.get_brief.return_value = self._setup_brief(brief_status=brief_status)

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.status_code == 404

    def test_preview_page_404s_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = self._setup_brief(user_id=234)

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")
        assert res.status_code == 404

    def test_preview_source_page_404s_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = self._setup_brief(user_id=234)

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.status_code == 404

    def test_preview_page_404s_if_brief_has_wrong_lot(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-outcomes/1234/preview")
        assert res.status_code == 404

    def test_preview_source_page_404s_if_brief_has_wrong_lot(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-outcomes/1234/preview-source")
        assert res.status_code == 404

    def test_preview_page_400s_if_unanswered_questions(self):
        brief_json = self._setup_brief()
        brief_json['briefs'].pop('essentialRequirements')
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")
        assert res.status_code == 400

        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        # Show link to the the unanswered question
        assert 'You still need to complete the following questions before your requirements can be previewed:' in \
               page_html
        assert len(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
              "digital-specialists/1234/edit/shortlist-and-evaluation-process/technicalCompetenceCriteriaSpecialists",
            t="Technical competence criteria",
        )) == 1

        # Don't show the preview tabs or call-to-action button
        assert "This is how suppliers will see your requirements when they are published." not in page_html
        preview_src_link = "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/" \
                           "digital-specialists/1234/preview-source"
        assert len(document.xpath(
            "//iframe[@src=$u][@title=$t][@class=$c]",
            u=preview_src_link,
            t="Preview of the page on desktop or tablet",
            c="dm-desktop-iframe"
        )) == 0
        assert len(document.xpath(
            "//button[normalize-space(string())=$t]",
            t="Confirm your requirements and publish",
        )) == 0

    def test_preview_source_page_400s_if_unanswered_questions(self):
        brief_json = self._setup_brief()
        brief_json['briefs'].pop('essentialRequirements')
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.status_code == 400

    def test_preview_page_renders_tabs_and_iframes(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)
        assert "This is how suppliers see your requirements when they are published." in page_html
        assert len(document.xpath('//div[@class="govuk-tabs"]//a[contains(text(), "Desktop")]')) == 1

        expected_src_link = "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/" \
                            "digital-specialists/1234/preview-source"
        assert len(document.xpath(
            "//iframe[@src=$u][@title=$t][@class=$c]",
            u=expected_src_link,
            t="Preview of the page on desktop or tablet",
            c="dm-desktop-iframe"
        )) == 1
        assert len(document.xpath(
            "//iframe[@src=$u][@title=$t][@class=$c]",
            u=expected_src_link,
            t="Preview of the page on mobile",
            c="dm-mobile-iframe"
        )) == 1

        assert len(document.xpath(
            "//button[normalize-space(string())=$t]",
            t="Confirm your requirements and publish",
        )) == 1

    def test_preview_source_page_renders_default_application_statistics(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        incomplete_responses_section = document.xpath('//div[@id="incomplete-applications"]')[0]
        completed_responses_section = document.xpath('//div[@id="completed-applications"]')[0]

        assert incomplete_responses_section.xpath('h2//span[1]/text()')[0] == '0'
        assert incomplete_responses_section.xpath('h2//span[2]/text()')[0] == "Incomplete applications"
        assert incomplete_responses_section.xpath('p[1]/text()')[0] == "0 SME, 0 large"

        assert completed_responses_section.xpath('h2//span[1]/text()')[0] == '0'
        assert completed_responses_section.xpath('h2//span[2]/text()')[0] == "Completed applications"
        assert completed_responses_section.xpath('p[1]/text()')[0] == "0 SME, 0 large"

    def test_preview_source_page_renders_default_important_dates(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()

        with freeze_time('2019-01-01 11:08:00'):
            res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                                  "digital-specialists/1234/preview-source")
        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        important_dates = document.xpath('(//dl[@id="opportunity-important-dates"]//div)')

        assert len(important_dates) == 3
        assert important_dates[0].xpath('dt')[0].text_content().strip() \
            == "Published"
        assert important_dates[0].xpath('dd')[0].text_content().strip() \
            == "Tuesday 1 January 2019"
        assert important_dates[1].xpath('dt')[0].text_content().strip() \
            == "Deadline for asking questions"
        assert important_dates[1].xpath('dd')[0].text_content().strip() \
            == "Thursday 3 January 2019 at 11:59pm GMT"
        assert important_dates[2].xpath('dt')[0].text_content().strip() \
            == "Closing date for applications"
        assert important_dates[2].xpath('dd')[0].text_content().strip() \
            == "Tuesday 8 January 2019 at 11:59pm GMT"

    @pytest.mark.parametrize('brief_q_and_a_link', [True, False])
    def test_preview_source_page_shows_optional_question_and_answer_session_link(self, brief_q_and_a_link):
        brief_json = self._setup_brief()
        if brief_q_and_a_link:
            brief_json['briefs']['questionAndAnswerSessionDetails'] = \
                "A paragraph of details that get shown on another, login-protected page"
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)
        assert bool(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u='#',
            t="View question and answer session details"
        )) == brief_q_and_a_link

    def test_preview_source_page_shows_apply_button_and_ask_a_question_links(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()
        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)
        assert "No questions have been answered yet" in page_html
        assert len(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="#",
            t="Log in to ask a question",
        )) == 1

    @pytest.mark.parametrize(
        'disabled_link_text, count',
        [
            ('GOV.UK Digital Marketplace', 1),
            ('Digital Marketplace', 1),
            ('Supplier opportunities', 1),
            ('Guidance', 1),
            ('Help', 1),
            ('Log in', 1),
            ('send your feedback', 1),
        ]
    )
    def test_preview_source_page_shows_disabled_header_breadcrumbs_and_footer_links(self, disabled_link_text, count):
        self.data_api_client.get_brief.return_value = self._setup_brief()
        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert len(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="#",
            t=disabled_link_text,
        )) == count, f"could not find link '{disabled_link_text}' with href '#'"

    def test_preview_source_page_will_open_user_generated_links_in_a_new_tab(self):
        brief_json = self._setup_brief()
        brief_json['briefs']['summary'] = "A link to the full summary: https://www.example.com"
        self.data_api_client.get_brief.return_value = brief_json
        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert len(document.xpath(
            "//a[@href=$u][@target=$b][@rel=$r][normalize-space(string())=$t]",
            u="https://www.example.com",
            b="_blank",
            r="external noreferrer noopener",
            t="https://www.example.com",
        )) == 1

    def test_preview_page_xframe_options_header_not_set(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()
        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview")
        assert res.headers['X-Frame-Options'] == 'DENY'

    def test_preview_source_page_xframe_options_header_set(self):
        self.data_api_client.get_brief.return_value = self._setup_brief()
        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/preview-source")
        assert res.headers['X-Frame-Options'] == 'sameorigin'


class TestPublishBrief(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.publish.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug='digital-outcomes-and-specialists-4',
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

    def test_publish_brief(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'backgroundInformation': 'test background info',
            'contractLength': 'A very long time',
            'culturalFitCriteria': ['CULTURAL', 'FIT'],
            'culturalWeighting': 10,
            'essentialRequirements': 'Everything',
            'evaluationType': ['test evaluation type'],
            'existingTeam': 'team team team',
            'importantDates': 'Near future',
            'numberOfSuppliers': 5,
            'location': 'somewhere',
            'organisation': 'test organisation',
            'priceWeighting': 80,
            'specialistRole': 'communicationsManager',
            'specialistWork': 'work work work',
            'startDate': 'startDate',
            'summary': 'blah',
            'technicalWeighting': 10,
            'workingArrangements': 'arrangements',
            'workplaceAddress': 'address',
            'requirementsLength': '1 week'
        })
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.post("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                               "digital-specialists/1234/publish")
        assert res.status_code == 302
        assert self.data_api_client.publish_brief.called
        assert res.location == "http://localhost/buyers/frameworks/digital-outcomes-and-specialists-4/" \
                               "requirements/digital-specialists/1234?published=true"

    def test_publish_brief_with_unanswered_required_questions(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()

        res = self.client.post("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                               "digital-specialists/1234/publish")
        assert res.status_code == 400
        assert not self.data_api_client.publish_brief.called

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(user_id=234).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/your-organisation",
            data={
                "organisation": "GDS"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_brief_has_wrong_lot(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-outcomes/1234/edit/your-organisation",
            data={
                "organisation": "GDS"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_framework_status_is_not_live(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill', 'expired']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists-4',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response()
                ]
            ).single_result_response()

            brief_json = BriefStub(status="draft").single_result_response()
            brief_questions = brief_json['briefs']
            brief_questions.update({
                'backgroundInformation': 'test background info',
                'contractLength': 'A very long time',
                'culturalFitCriteria': ['CULTURAL', 'FIT'],
                'culturalWeighting': 10,
                'essentialRequirements': 'Everything',
                'evaluationType': ['test evaluation type'],
                'existingTeam': 'team team team',
                'importantDates': 'Near future',
                'numberOfSuppliers': 5,
                'location': 'somewhere',
                'organisation': 'test organisation',
                'priceWeighting': 80,
                'specialistRole': 'communicationsManager',
                'specialistWork': 'work work work',
                'startDate': 'startDate',
                'summary': 'blah',
                'technicalWeighting': 10,
                'workingArrangements': 'arrangements',
                'workplaceAddress': 'address',
                'requirementsLength': '1 week'
            })
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.post("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                                   "digital-specialists/1234/publish")
            assert res.status_code == 404
            assert not self.data_api_client.publish_brief.called

    def test_publish_button_available_if_questions_answered(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'backgroundInformation': 'test background info',
            'contractLength': 'A very long time',
            'culturalFitCriteria': ['CULTURAL', 'FIT'],
            'culturalWeighting': 10,
            'essentialRequirements': 'Everything',
            'evaluationType': ['test evaluation type'],
            'existingTeam': 'team team team',
            'importantDates': 'Near future',
            'location': 'somewhere',
            'numberOfSuppliers': 3,
            'organisation': 'test organisation',
            'priceWeighting': 80,
            'specialistRole': 'communicationsManager',
            'specialistWork': 'work work work',
            'startDate': 'startDate',
            'summary': 'blah',
            'technicalWeighting': 10,
            'workingArrangements': 'arrangements',
            'workplaceAddress': 'address',
            'requirementsLength': '1 week'
        })
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/publish")
        page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'Publish requirements' in page_html, page_html

    def test_publish_button_unavailable_if_questions_not_answered(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'requirementsLength': '1 week'
        })
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/publish")
        page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'Publish requirements' not in page_html

    def test_warning_about_setting_requirement_length_is_not_displayed_if_not_specialist_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response()
            ]
        ).single_result_response()

        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            lot_slug="digital-outcomes",
            status="draft",
        ).single_result_response()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-outcomes/1234/publish")
        page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'This will show you what the supplier application deadline will be' not in page_html
        assert 'Your requirements will be open for 2 weeks' in page_html

    def test_correct_content_is_displayed_if_no_requirementLength_is_set(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/publish")
        page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'href="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/edit/set-how-long-your-requirements-will-be-open-for/requirementsLength"' in page_html  # noqa
        assert 'This will show you what the supplier application deadline will be' in page_html
        assert 'Your requirements will be open for' not in page_html

    def test_correct_content_is_displayed_if_requirementLength_is_1_week(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'requirementsLength': '1 week'
        })
        self.data_api_client.get_brief.return_value = brief_json

        with freeze_time('2016-12-31 23:59:59'):
            res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                                  "digital-specialists/1234/publish")
            page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'Your requirements will be open for 1 week.' in page_html
        assert 'This will show you what the supplier application deadline will be' not in page_html
        assert 'Your requirements will be open for 2 weeks' not in page_html
        assert 'If you publish your requirements today (31 December)' in page_html
        assert 'suppliers will be able to apply until Saturday 7 January 2017 at 11:59pm GMT' in page_html

    def test_correct_content_is_displayed_if_requirementLength_is_2_weeks(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'requirementsLength': '2 weeks'
        })
        self.data_api_client.get_brief.return_value = brief_json

        with freeze_time('2017-07-17 23:59:59'):
            res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                                  "digital-specialists/1234/publish")
            page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'Your requirements will be open for 2 weeks.' in page_html
        assert 'This will show you what the supplier application deadline will be' not in page_html
        assert 'Your requirements will be open for 1 week' not in page_html
        assert 'If you publish your requirements today (17 July)' in page_html
        assert 'suppliers will be able to apply until Monday 31 July 2017 at 11:59pm GMT' in page_html

    def test_correct_content_is_displayed_if_requirementLength_is_not_set(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'requirementsLength': None
        })
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/publish")
        page_html = res.get_data(as_text=True)
        document = html.fromstring(page_html)

        assert res.status_code == 200
        assert 'Your requirements will be open for 2 weeks.' not in page_html
        assert 'This will show you what the supplier application deadline will be' in page_html
        assert 'Your requirements will be open for 1 week' not in page_html
        assert not document.xpath('//a[contains(text(), "Set how long your requirements will be live for")]')

    def test_heading_for_unanswered_questions_not_displayed_if_only_requirements_length_unset(self):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'backgroundInformation': 'test background info',
            'contractLength': 'A very long time',
            'culturalFitCriteria': ['CULTURAL', 'FIT'],
            'culturalWeighting': 10,
            'essentialRequirements': 'Everything',
            'evaluationType': ['test evaluation type'],
            'existingTeam': 'team team team',
            'importantDates': 'Near future',
            'location': 'somewhere',
            'numberOfSuppliers': 3,
            'organisation': 'test organisation',
            'priceWeighting': 80,
            'specialistRole': 'communicationsManager',
            'specialistWork': 'work work work',
            'startDate': 'startDate',
            'summary': 'blah',
            'technicalWeighting': 10,
            'workingArrangements': 'arrangements',
            'workplaceAddress': 'address'
        })
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get("/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
                              "digital-specialists/1234/publish")
        page_html = res.get_data(as_text=True)

        assert res.status_code == 200
        assert "You still need to complete the following questions before your requirements " \
            "can be published:" not in page_html


class TestViewQuestionAndAnswerDates(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.publish.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_show_question_and_answer_dates_for_published_brief(self):
        for framework_status in ['live', 'expired']:
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
            brief_json['briefs']['requirementsLength'] = '2 weeks'
            brief_json['briefs']['publishedAt'] = u"2016-04-02T20:10:00.00000Z"
            brief_json['briefs']['clarificationQuestionsClosedAt'] = u"2016-04-12T23:59:00.00000Z"
            brief_json['briefs']['clarificationQuestionsPublishedBy'] = u"2016-04-14T23:59:00.00000Z"
            brief_json['briefs']['applicationsClosedAt'] = u"2016-04-16T23:59:00.00000Z"
            brief_json['briefs']['specialistRole'] = 'communicationsManager'
            brief_json['briefs']["clarificationQuestionsAreClosed"] = True
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/timeline"
            )

            assert res.status_code == 200
            page_html = res.get_data(as_text=True)
            document = html.fromstring(page_html)

            assert (document.xpath('//h1')[0]).text_content().strip() == "Question and answer dates"
            assert all(
                date in
                [e.text_content() for e in document.xpath('//main//th/span')]
                for date in ['2 April', '8 April', '15 April', '16 April']
            )

    def test_404_if_framework_is_not_live_or_expired(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
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
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/timeline"
            )

            assert res.status_code == 404

    def test_do_not_show_question_and_answer_dates_for_draft_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status="draft",
        ).single_result_response()
        brief_json['briefs']['specialistRole'] = 'communicationsManager'
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/timeline"
        )

        assert res.status_code == 404

    def test_do_not_show_question_and_answer_dates_for_closed_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
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
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/timeline"
        )

        assert res.status_code == 404
