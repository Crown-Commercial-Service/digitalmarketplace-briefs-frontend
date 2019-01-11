# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmapiclient import HTTPError
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub
import mock
from lxml import html
import pytest


class TestClarificationQuestionsPage(BaseApplicationTest):

    SIDE_LINKS_XPATH = '//div[@class="column-one-third"]//a'
    INSTRUCTION_LINKS_XPATH = '//main[@id="content"]//ul/li/a'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.supplier_questions.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
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
    def test_show_clarification_questions_page_for_live_brief_with_no_questions(
            self, framework_status):
        with self.app.app_context():

            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            brief_json = BriefStub(status="live").single_result_response()
            brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
            )

            assert res.status_code == 200
            page_html = res.get_data(as_text=True)
            assert "Supplier questions" in page_html
            assert "No questions or answers have been published" in page_html
            assert "Answer a supplier question" in page_html

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_clarification_questions_page_for_live_brief_with_one_question(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(status="live", clarification_questions=[
            {"question": "Why is my question a question?",
             "answer": "Because",
             "publishedAt": "2016-01-01T00:00:00.000000Z"}
        ]).single_result_response()
        brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
        brief_json['briefs']["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
        )

        assert res.status_code == 200
        page_html = res.get_data(as_text=True)
        assert "Supplier questions" in page_html
        assert "Why is my question a question?" in page_html
        assert "Because" in page_html
        assert "Answer a supplier question" in page_html
        assert "No questions or answers have been published" not in page_html

    def test_clarification_questions_page_returns_404_if_not_live_brief(self):
        self.data_api_client.get_brief.return_value = BriefStub(status="expired", clarification_questions=[
            {"question": "Why is my question a question?",
             "answer": "Because",
             "publishedAt": "2016-01-01T00:00:00.000000Z"}
        ]).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
        )

        assert res.status_code == 404

    def test_clarification_questions_page_returns_404_if_brief_not_correct(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),  # 'Incorrect' lot slug
            ]
        ).single_result_response()
        brief_json = BriefStub(status="live", clarification_questions=[
            {"question": "Why is my question a question?",
             "answer": "Because",
             "publishedAt": "2016-01-01T00:00:00.000000Z"}
        ]).single_result_response()
        brief_json['briefs']['lotSlug'] = "wrong lot slug"
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
        )

        assert res.status_code == 404


class TestAddBriefClarificationQuestion(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.supplier_questions.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists",
            status="live",
            lots=[
                LotStub(slug="digital-specialists", allows_brief=True).response(),
            ]
        ).single_result_response()
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_show_brief_clarification_question_form_for_live_and_expired_framework(self):
        framework_statuses = ['live', 'expired']
        for framework_status in framework_statuses:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug="digital-outcomes-and-specialists",
                status=framework_status,
                lots=[
                    LotStub(slug="digital-specialists", allows_brief=True).response(),
                ]
            ).single_result_response()
            brief_json = BriefStub(status="live").single_result_response()
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question")

            assert res.status_code == 200

    def test_add_brief_clarification_question_for_live_and_expired_framework(self):
        framework_statuses = ['live', 'expired']
        for framework_status in framework_statuses:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug="digital-outcomes-and-specialists",
                status=framework_status,
                lots=[
                    LotStub(slug="digital-specialists", allows_brief=True).response(),
                ]
            ).single_result_response()
            brief_json = BriefStub(status="live").single_result_response()
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question",
                data={
                    "question": "Why?",
                    "answer": "Because",
                })

            assert res.status_code == 302
            self.data_api_client.add_brief_clarification_question.assert_called_with(
                "1234", "Why?", "Because", "buyer@email.com")

            # test that the redirect ends up on the right page
            assert res.headers['Location'].endswith(
                '/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions'  # noqa
            ) is True

    def test_404_if_framework_is_not_live_or_expired(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            brief_json = BriefStub().single_result_response()
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            self.data_api_client.get_brief.return_value = brief_json

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question",
                data={
                    "question": "Why?",
                    "answer": "Because",
                })

            assert res.status_code == 404
            assert not self.data_api_client.add_brief_clarification_question.called

    def test_404_if_framework_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub().single_result_response()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not self.data_api_client.add_brief_clarification_question.called

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        brief_json = BriefStub(user_id=234).single_result_response()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not self.data_api_client.add_brief_clarification_question.called

    def test_404_if_brief_is_not_live(self):
        brief_json = BriefStub(status="draft").single_result_response()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        self.data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not self.data_api_client.add_brief_clarification_question.called

    def test_validation_error(self):
        brief_json = BriefStub(status="live").single_result_response()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        self.data_api_client.get_brief.return_value = brief_json
        self.data_api_client.add_brief_clarification_question.side_effect = HTTPError(
            mock.Mock(status_code=400),
            {"question": "answer_required"})

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 400
        assert len(document.cssselect(".validation-message")) == 1, res.get_data(as_text=True)

    def test_api_error(self):
        brief_json = BriefStub(status="live").single_result_response()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        self.data_api_client.get_brief.return_value = brief_json
        self.data_api_client.add_brief_clarification_question.side_effect = HTTPError(
            mock.Mock(status_code=500))

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 500
