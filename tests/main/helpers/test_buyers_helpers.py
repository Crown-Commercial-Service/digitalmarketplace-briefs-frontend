import mock
import pytest
from werkzeug.exceptions import NotFound

import app.main.helpers as helpers
from dmcontent.content_loader import ContentLoader

from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

content_loader = ContentLoader('tests/fixtures/content')
content_loader.load_manifest('dos', 'data', 'edit_brief')
questions_builder = content_loader.get_manifest('dos', 'edit_brief')


class TestBuyersHelpers(object):
    def test_get_framework_and_lot(self):
        provided_lot = LotStub(slug='digital-specialists', allows_brief=True).response()
        data_api_client = mock.Mock()
        data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[provided_lot],
        ).single_result_response()

        framework, lot = helpers.buyers_helpers.get_framework_and_lot('digital-outcomes-and-specialists',
                                                                      'digital-specialists',
                                                                      data_api_client)

        assert framework['status'] == "live"
        assert framework['name'] == 'Digital Outcomes and Specialists'
        assert framework['slug'] == 'digital-outcomes-and-specialists'
        assert framework['clarificationQuestionsOpen'] is True
        assert lot == provided_lot

    def test_get_framework_and_lot_404s_for_wrong_framework_status(self):
        data_api_client = mock.Mock()
        data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='open',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        with pytest.raises(NotFound):
            helpers.buyers_helpers.get_framework_and_lot(
                'digital-outcomes-and-specialists',
                'digital-specialists',
                data_api_client,
                allowed_statuses=['live'],
            )

    def test_get_framework_and_lot_404s_if_allows_brief_required(self):
        data_api_client = mock.Mock()
        data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        with pytest.raises(NotFound):
            helpers.buyers_helpers.get_framework_and_lot(
                'digital-outcomes-and-specialists',
                'digital-specialists',
                data_api_client,
                must_allow_brief=True,
            )

    @pytest.mark.parametrize(
        ['framework', 'lot', 'user', 'result'],
        [
            ('digital-outcomes-and-specialists', 'digital-specialists', 123, True),
            ('not-digital-outcomes-and-specialists', 'digital-specialists', 123, False),
            ('digital-outcomes-and-specialists', 'not-digital-specialists', 123, False),
            ('digital-outcomes-and-specialists', 'digital-specialists', 124, False),
        ]
    )
    def test_is_brief_correct(self, framework, lot, user, result):
        brief = BriefStub(user_id=123, status='live').response()

        assert helpers.buyers_helpers.is_brief_correct(brief, framework, lot, user) is result

    @pytest.mark.parametrize(
        ['status', 'allow_withdrawn', 'result'],
        [
            ('withdrawn', True, True),
            ('withdrawn', False, False),
            ('live', True, True),
            ('live', False, True),
        ]
    )
    def test_if_brief_correct_allow_withdrawn(self, status, allow_withdrawn, result):
        brief = BriefStub(user_id=123, status=status).response()
        assert helpers.buyers_helpers.is_brief_correct(
            brief, 'digital-outcomes-and-specialists', 'digital-specialists', 123, allow_withdrawn=allow_withdrawn
        ) is result

    @pytest.mark.parametrize(
        'allowed_statuses, result', [
            (['live', 'closed'], True),
            (['closed'], False)
        ]
    )
    def test_is_brief_correct_allowed_statuses(self, allowed_statuses, result):
        brief = BriefStub(user_id=123, status='live').response()
        assert helpers.buyers_helpers.is_brief_correct(
            brief, 'digital-outcomes-and-specialists', 'digital-specialists', 123, allowed_statuses=allowed_statuses
        ) is result

    def test_is_brief_associated_with_user(self):
        brief = BriefStub(user_id=123).response()
        assert helpers.buyers_helpers.is_brief_associated_with_user(brief, 123) is True
        assert helpers.buyers_helpers.is_brief_associated_with_user(brief, 234) is False

    def test_brief_can_be_edited(self):
        assert helpers.buyers_helpers.brief_can_be_edited(BriefStub(status='draft').response()) is True
        assert helpers.buyers_helpers.brief_can_be_edited(BriefStub(status='live').response()) is False

    def test_brief_is_withdrawn(self):
        assert helpers.buyers_helpers.brief_is_withdrawn(BriefStub(status='withdrawn').response()) is True
        assert helpers.buyers_helpers.brief_is_withdrawn(BriefStub(status='live').response()) is False

    def test_section_has_at_least_one_required_question(self):
        content = content_loader.get_manifest('dos', 'edit_brief').filter(
            {'lot': 'digital-specialists'}
        )

        sections_with_required_questions = {
            'section-1': True,
            'section-2': True,
            'section-4': False,
            'section-5': True
        }

        for section in content.sections:
            assert helpers.buyers_helpers.section_has_at_least_one_required_question(section) \
                == sections_with_required_questions[section.slug]

    def test_count_unanswered_questions(self):
        brief = {
            'status': 'draft',
            'frameworkSlug': 'dos',
            'lotSlug': 'digital-specialists',
            'required1': True
        }
        content = content_loader.get_manifest('dos', 'edit_brief').filter(
            {'lot': 'digital-specialists'}
        )
        sections = content.summary(brief)

        unanswered_required, unanswered_optional = helpers.buyers_helpers.count_unanswered_questions(sections)
        assert unanswered_required == 2
        assert unanswered_optional == 2

    def test_add_unanswered_counts_to_briefs(self):
        briefs = [{
            'status': 'draft',
            'frameworkSlug': 'dos',
            'lotSlug': 'digital-specialists',
            'required1': True
        }]

        assert helpers.buyers_helpers.add_unanswered_counts_to_briefs(briefs, content_loader) == [{
            'status': 'draft',
            'frameworkSlug': 'dos',
            'lotSlug': 'digital-specialists',
            'required1': True,
            'unanswered_required': 2,
            'unanswered_optional': 2
        }]

    def test_get_sorted_responses_for_brief(self):
        data_api_client = mock.Mock()
        data_api_client.find_brief_responses.return_value = {
            "briefResponses": [
                {"id": "five", "niceToHaveRequirements": [True, True, True, True, True]},
                {"id": "zero", "niceToHaveRequirements": [False, False, False, False, False]},
                {"id": "three", "niceToHaveRequirements": [True, True, False, False, True]},
                {"id": "five", "niceToHaveRequirements": [True, True, True, True, True]},
                {"id": "four", "niceToHaveRequirements": [True, True, True, True, False]},
                {"id": "one", "niceToHaveRequirements": [False, False, False, True, False]},
                {"id": "four", "niceToHaveRequirements": [True, True, True, True, False]},
            ]
        }
        brief = {"id": 1, "niceToHaveRequirements": ["Nice", "to", "have", "yes", "please"]}

        assert helpers.buyers_helpers.get_sorted_responses_for_brief(brief, data_api_client) == [
            {'id': 'five', 'niceToHaveRequirements': [True, True, True, True, True]},
            {'id': 'five', 'niceToHaveRequirements': [True, True, True, True, True]},
            {'id': 'four', 'niceToHaveRequirements': [True, True, True, True, False]},
            {'id': 'four', 'niceToHaveRequirements': [True, True, True, True, False]},
            {'id': 'three', 'niceToHaveRequirements': [True, True, False, False, True]},
            {"id": "one", "niceToHaveRequirements": [False, False, False, True, False]},
            {'id': 'zero', 'niceToHaveRequirements': [False, False, False, False, False]}
        ]

    def test_get_sorted_responses_does_not_sort_if_no_nice_to_haves(self):
        data_api_client = mock.Mock()
        data_api_client.find_brief_responses.return_value = {
            "briefResponses": [
                {"id": "five"},
                {"id": "zero"},
                {"id": "three"},
                {"id": "five"}
            ]
        }
        brief = {"id": 1, "niceToHaveRequirements": []}
        assert helpers.buyers_helpers.get_sorted_responses_for_brief(brief, data_api_client) == [
            {"id": "five"},
            {"id": "zero"},
            {"id": "three"},
            {"id": "five"}
        ]
