# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmapiclient import api_stubs, HTTPError
import mock
from lxml import html
import pytest


@mock.patch('app.main.views.supplier_questions.data_api_client', autospec=True)
class TestClarificationQuestionsPage(BaseApplicationTest):

    SIDE_LINKS_XPATH = '//div[@class="column-one-third"]//a'
    INSTRUCTION_LINKS_XPATH = '//main[@id="content"]//ul/li/a'

    @staticmethod
    def _get_links(document, xpath, text_only=None):
        if text_only:
            return [e.text_content() for e in document.xpath(xpath)]
        return [
            (e.text_content(), e.get('href')) for e in document.xpath(xpath)
        ]

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_clarification_questions_page_for_live_brief_with_no_questions(
            self, data_api_client, framework_status):
        with self.app.app_context():
            self.login_as_buyer()
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    api_stubs.lot(slug='digital-specialists', allows_brief=True),
                ]
            )
            brief_json = api_stubs.brief(status="live")
            brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
            )

            assert res.status_code == 200
            page_html = res.get_data(as_text=True)
            assert "Supplier questions" in page_html
            assert "No questions or answers have been published" in page_html
            assert "Answer a supplier question" in page_html

    @pytest.mark.parametrize('framework_status', ['live', 'expired'])
    def test_show_clarification_questions_page_for_live_brief_with_one_question(
            self, data_api_client, framework_status):
        with self.app.app_context():
            self.login_as_buyer()
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    api_stubs.lot(slug='digital-specialists', allows_brief=True),
                ]
            )
            brief_json = api_stubs.brief(status="live", clarification_questions=[
                {"question": "Why is my question a question?",
                 "answer": "Because",
                 "publishedAt": "2016-01-01T00:00:00.000000Z"}
            ])
            brief_json['briefs']['publishedAt'] = "2016-04-02T20:10:00.00000Z"
            brief_json['briefs']["clarificationQuestionsAreClosed"] = True
            data_api_client.get_brief.return_value = brief_json

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

    def test_clarification_questions_page_returns_404_if_not_live_brief(self, data_api_client):
        with self.app.app_context():
            self.login_as_buyer()
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug='digital-outcomes-and-specialists',
                status='live',
                lots=[
                    api_stubs.lot(slug='digital-specialists', allows_brief=True),
                ]
            )
            data_api_client.get_brief.return_value = api_stubs.brief(status="expired", clarification_questions=[
                {"question": "Why is my question a question?",
                 "answer": "Because",
                 "publishedAt": "2016-01-01T00:00:00.000000Z"}
            ])

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
            )

            assert res.status_code == 404

    def test_clarification_questions_page_returns_404_if_brief_not_correct(self, data_api_client):
        with self.app.app_context():
            self.login_as_buyer()
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug='digital-outcomes-and-specialists',
                status='live',
                lots=[
                    api_stubs.lot(slug='digital-specialists', allows_brief=True),  # 'Incorrect' lot slug
                ]
            )
            brief_json = api_stubs.brief(status="live", clarification_questions=[
                {"question": "Why is my question a question?",
                 "answer": "Because",
                 "publishedAt": "2016-01-01T00:00:00.000000Z"}
            ])
            brief_json['briefs']['lotSlug'] = "wrong lot slug"
            data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions"  # noqa
            )

            assert res.status_code == 404


@mock.patch("app.main.views.supplier_questions.data_api_client", autospec=True)
class TestAddBriefClarificationQuestion(BaseApplicationTest):
    def test_show_brief_clarification_question_form_for_live_and_expired_framework(self, data_api_client):
        framework_statuses = ['live', 'expired']
        self.login_as_buyer()
        for framework_status in framework_statuses:
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug="digital-outcomes-and-specialists",
                status=framework_status,
                lots=[
                    api_stubs.lot(slug="digital-specialists", allows_brief=True)
                ])
            brief_json = api_stubs.brief(status="live")
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            data_api_client.get_brief.return_value = brief_json

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question")

            assert res.status_code == 200

    def test_add_brief_clarification_question_for_live_and_expired_framework(self, data_api_client):
        framework_statuses = ['live', 'expired']
        self.login_as_buyer()
        for framework_status in framework_statuses:
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug="digital-outcomes-and-specialists",
                status=framework_status,
                lots=[
                    api_stubs.lot(slug="digital-specialists", allows_brief=True)
                ])
            brief_json = api_stubs.brief(status="live")
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            data_api_client.get_brief.return_value = brief_json

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question",
                data={
                    "question": "Why?",
                    "answer": "Because",
                })

            assert res.status_code == 302
            data_api_client.add_brief_clarification_question.assert_called_with(
                "1234", "Why?", "Because", "buyer@email.com")

            # test that the redirect ends up on the right page
            assert res.headers['Location'].endswith(
                '/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/supplier-questions'  # noqa
            ) is True

    def test_404_if_framework_is_not_live_or_expired(self, data_api_client):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
            self.login_as_buyer()
            data_api_client.get_framework.return_value = api_stubs.framework(
                slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    api_stubs.lot(slug='digital-specialists', allows_brief=True),
                ]
            )
            brief_json = api_stubs.brief()
            brief_json['briefs']["clarificationQuestionsAreClosed"] = False
            data_api_client.get_brief.return_value = brief_json

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
                "/digital-specialists/1234/supplier-questions/answer-question",
                data={
                    "question": "Why?",
                    "answer": "Because",
                })

            assert res.status_code == 404
            assert not data_api_client.add_brief_clarification_question.called

    def test_404_if_framework_does_not_allow_brief(self, data_api_client):
        self.login_as_buyer()
        data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=False),
            ]
        )
        brief_json = api_stubs.brief()
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not data_api_client.add_brief_clarification_question.called

    def test_404_if_brief_does_not_belong_to_user(self, data_api_client):
        self.login_as_buyer()
        data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=True),
            ]
        )
        brief_json = api_stubs.brief(user_id=234)
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not data_api_client.add_brief_clarification_question.called

    def test_404_if_brief_is_not_live(self, data_api_client):
        self.login_as_buyer()
        data_api_client.get_framework.return_value = api_stubs.framework(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                api_stubs.lot(slug='digital-specialists', allows_brief=True),
            ]
        )
        brief_json = api_stubs.brief(status="draft")
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        data_api_client.get_brief.return_value = brief_json

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 404
        assert not data_api_client.add_brief_clarification_question.called

    def test_validation_error(self, data_api_client):
        self.login_as_buyer()
        data_api_client.get_framework.return_value = api_stubs.framework(
            slug="digital-outcomes-and-specialists",
            status="live",
            lots=[
                api_stubs.lot(slug="digital-specialists", allows_brief=True)
            ])
        brief_json = api_stubs.brief(status="live")
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        data_api_client.get_brief.return_value = brief_json
        data_api_client.add_brief_clarification_question.side_effect = HTTPError(
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

    def test_api_error(self, data_api_client):
        self.login_as_buyer()
        data_api_client.get_framework.return_value = api_stubs.framework(
            slug="digital-outcomes-and-specialists",
            status="live",
            lots=[
                api_stubs.lot(slug="digital-specialists", allows_brief=True)
            ])
        brief_json = api_stubs.brief(status="live")
        brief_json['briefs']["clarificationQuestionsAreClosed"] = False
        data_api_client.get_brief.return_value = brief_json
        data_api_client.add_brief_clarification_question.side_effect = HTTPError(
            mock.Mock(status_code=500))

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements"
            "/digital-specialists/1234/supplier-questions/answer-question",
            data={
                "question": "Why?",
                "answer": "Because",
            })

        assert res.status_code == 500
