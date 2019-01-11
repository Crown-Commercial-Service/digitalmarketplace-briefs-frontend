# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmcontent.content_loader import ContentLoader
from dmcontent.questions import Question
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub
import mock
from lxml import etree
import pytest

from zipfile import ZipFile
from io import BytesIO

from app.main.views import download_responses
from dmapiclient import DataAPIClient
import functools
import inflection

from werkzeug.exceptions import NotFound


po = functools.partial(mock.patch.object, autospec=True)


class TestDownloadBriefResponsesView(BaseApplicationTest):
    def setup_method(self, method):
        super(TestDownloadBriefResponsesView, self).setup_method(method)

        self.data_api_client = mock.MagicMock(spec_set=DataAPIClient)
        self.content_loader = mock.MagicMock(spec_set=ContentLoader)

        self.instance = download_responses.DownloadBriefResponsesView()
        self.instance.data_api_client = self.data_api_client
        self.instance.content_loader = self.content_loader

        self.brief = BriefStub(status='closed', user_id=123).response()
        self.brief['essentialRequirements'] = [
            "Good nose for tea",
            "Good eye for biscuits",
            "Knowledgable about tea"
        ]
        self.brief['niceToHaveRequirements'] = [
            "Able to bake",
            "Able to perform the tea ceremony"
        ]
        self.brief['blah'] = ['Affirmative', 'Negative']

        self.responses = [
            {
                "supplierName": "Prof. T. Maker",
                "respondToEmailAddress": "t.maker@example.com",
                "niceToHaveRequirements": [
                    {
                        "yesNo": False
                    },
                    {
                        "yesNo": False
                    }
                ],
                "availability": "2017-12-25",
                "essentialRequirementsMet": True,
                "essentialRequirements": [
                    {
                        "evidence": "From Assan to Yixing I've got you covered."
                    },
                    {
                        "evidence": "There will be no nobhobs or cream custards on my watch."
                    },
                    {
                        "evidence": "Here is a bad character >\u001e<"
                    }
                ],
                "dayRate": "750",
                "blah": [True, False]
            },
            {
                "supplierName": "Tea Boy Ltd.",
                "respondToEmailAddress": "teaboy@example.com",
                "niceToHaveRequirements": [
                    {
                        "yesNo": True,
                        "evidence": "Winner of GBBO 2009"
                    },
                    {
                        "yesNo": True,
                        "evidence": "Currently learning from the re-incarnation of Eisai himself"
                    }
                ],
                "availability": "Tomorrow",
                "essentialRequirementsMet": True,
                "essentialRequirements": [
                    {
                        "evidence": "I know my Silver needle from my Red lychee"
                    },
                    {
                        "evidence": "Able to identify fake hobnobs and custard cremes a mile off"
                    },
                    {
                        "evidence": "Have visited the Flagstaff House Museum of Tea Ware in Hong Kong"
                    }
                ],
                "dayRate": "1000",
                "blah": [False, True]
            }
        ]

    def teardown_method(self, method):
        self.instance = None

        super(TestDownloadBriefResponsesView, self).teardown_method(method)

    @pytest.mark.parametrize('brief_status', download_responses.CLOSED_PUBLISHED_BRIEF_STATUSES)
    def test_end_to_end_for_closed_awarded_cancelled_unsuccessful_briefs(self, brief_status):
        self.brief['status'] = brief_status
        if brief_status == 'awarded':
            self.brief['awardedBriefResponseId'] = 999
        for framework_status in ['live', 'expired']:
            self.data_api_client.find_brief_responses.return_value = {
                'briefResponses': self.responses
            }
            self.data_api_client.get_framework.return_value = FrameworkStub(
                framework_slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            self.data_api_client.get_brief.return_value = {'briefs': self.brief}

            with mock.patch.object(download_responses, 'data_api_client', self.data_api_client):
                self.login_as_buyer()
                res = self.client.get(
                    "/buyers/frameworks/digital-outcomes-and-specialists"
                    "/requirements/digital-specialists/1234/responses/download"
                )

            assert res.status_code == 200
            assert res.mimetype == 'application/vnd.oasis.opendocument.spreadsheet'
            assert len(res.data) > 100

            self._check_xml_files_in_zip_are_well_formed(res.data)

    def _check_xml_files_in_zip_are_well_formed(self, raw_bytes):
        with BytesIO(raw_bytes) as buffer, ZipFile(buffer) as ods_as_zip:
            xml_files = (f for f in ods_as_zip.namelist() if f.endswith('.xml'))
            for filename in xml_files:
                with ods_as_zip.open(filename) as xml_data:
                    etree.parse(xml_data)  # throws if not well-formed

    def test_404_if_framework_is_not_live_or_expired(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
            self.data_api_client.find_brief_responses.return_value = {
                'briefResponses': self.responses
            }
            self.data_api_client.get_framework.return_value = FrameworkStub(
                framework_slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            self.data_api_client.get_brief.return_value = {'briefs': self.brief}

            with mock.patch.object(download_responses, 'data_api_client', self.data_api_client):
                self.login_as_buyer()
                res = self.client.get(
                    "/buyers/frameworks/digital-outcomes-and-specialists"
                    "/requirements/digital-specialists/1234/responses/download"
                )

            assert res.status_code == 404

    def test_get_responses(self):
        brief = mock.Mock()

        with po(download_responses, 'get_sorted_responses_for_brief') as m:
            result = self.instance.get_responses(brief)

        assert result == m.return_value

        m.assert_called_once_with(brief, self.instance.data_api_client)

    def test_get_question(self):
        framework_slug = mock.Mock()
        lot_slug = mock.Mock()
        manifest = mock.Mock()

        obj = self.content_loader.get_manifest.return_value
        content = obj.filter.return_value

        result = self.instance.get_questions(framework_slug, lot_slug, manifest)

        assert result == content.get_section.return_value.questions

        self.content_loader.get_manifest\
            .assert_called_once_with(framework_slug, manifest)

        obj.filter.assert_called_once_with({'lot': lot_slug}, dynamic=False)

        content.get_section\
               .assert_called_once_with('view-response-to-requirements')

    def test_get_question_fails_with_empty_list(self):
        framework_slug = mock.Mock()
        lot_slug = mock.Mock()
        manifest = mock.Mock()

        self.content_loader.get_manifest.return_value\
                           .filter.return_value\
                           .get_section.return_value = None

        result = self.instance.get_questions(framework_slug, lot_slug, manifest)

        assert result == []

    def test_get_file_context(self):
        self.instance.get_responses = mock.Mock()

        brief = BriefStub(status='closed').single_result_response()

        kwargs = {
            'brief_id': mock.Mock(),
            'framework_slug': mock.Mock(),
            'lot_slug': mock.Mock()
        }

        expected = {}
        expected['brief'] = brief['briefs']
        expected['responses'] = self.instance.get_responses.return_value
        expected['filename'] = 'supplier-responses-{}'.format(inflection.parameterize(str(brief['briefs']['title'])))

        self.instance.data_api_client.get_brief.return_value = brief

        with po(download_responses, 'get_framework_and_lot'),\
                po(download_responses, 'is_brief_correct') as is_brief_correct,\
                mock.patch.object(download_responses, 'current_user') as current_user:

            result = self.instance.get_file_context(**kwargs)

        is_brief_correct.assert_called_once_with(brief['briefs'],
                                                 kwargs['framework_slug'],
                                                 kwargs['lot_slug'],
                                                 current_user.id)

        self.instance.data_api_client.get_brief\
            .assert_called_once_with(kwargs['brief_id'])

        self.instance.get_responses\
            .assert_called_once_with(brief['briefs'])

        assert result == expected

    def test_get_file_context_with_incorrect_brief(self):
        self.instance.get_responses = mock.Mock()

        brief = BriefStub(status='closed').single_result_response()

        kwargs = {
            'brief_id': mock.Mock(),
            'framework_slug': mock.Mock(),
            'lot_slug': mock.Mock()
        }

        self.instance.data_api_client.get_brief.return_value = brief

        with po(download_responses, 'get_framework_and_lot'),\
                po(download_responses, 'is_brief_correct') as is_brief_correct,\
                mock.patch.object(download_responses, 'current_user'):

            is_brief_correct.return_value = False
            with pytest.raises(NotFound):
                self.instance.get_file_context(**kwargs)

    def test_get_file_context_with_open_brief(self):
        self.instance.get_responses = mock.Mock()

        brief = BriefStub(status='live').single_result_response()

        kwargs = {
            'brief_id': mock.Mock(),
            'framework_slug': mock.Mock(),
            'lot_slug': mock.Mock()
        }

        self.instance.data_api_client.get_brief.return_value = brief

        with po(download_responses, 'get_framework_and_lot'),\
                po(download_responses, 'is_brief_correct') as is_brief_correct,\
                mock.patch.object(download_responses, 'current_user'):

            is_brief_correct.return_value = True
            with pytest.raises(NotFound):
                self.instance.get_file_context(**kwargs)

    def test_populate_styled_ods_with_data(self):
        questions = [
            {'id': 'supplierName', 'name': 'Supplier', 'type': 'text'},
            {'id': 'respondToEmailAddress', 'name': 'Email address', 'type': 'text'},
            {'id': 'availability', 'name': 'Availability', 'type': 'text'},
            {'id': 'dayRate', 'name': 'Day rate', 'type': 'text'},
        ]

        self.instance.get_questions = mock.Mock(return_value=[
            Question(question) for question in questions
        ])

        doc = self.instance.populate_styled_ods_with_data(self.instance.create_blank_ods_with_styles(),
                                                          {'brief': self.brief, 'responses': self.responses})

        sheet = doc.sheet("Supplier evidence")

        assert sheet.read_cell(0, 0) == self.brief['title']

        for i, question in enumerate(questions):
            assert sheet.read_cell(0, i + 1) == question['name']
            assert sheet.read_cell(1, i + 1) == ''

            for j, response in enumerate(self.responses):
                assert sheet.read_cell(j + 2, i + 1) == response[question['id']]

    def test_populate_styled_ods_with_data_with_boolean_list(self):
        questions = [
            {'id': 'blah', 'name': 'Blah Blah', 'type': 'boolean_list'},
        ]

        self.instance.get_questions = mock.Mock(return_value=[
            Question(question) for question in questions
        ])

        doc = self.instance.populate_styled_ods_with_data(self.instance.create_blank_ods_with_styles(),
                                                          {'brief': self.brief, 'responses': self.responses})

        sheet = doc.sheet("Supplier evidence")

        row = 0
        for question in questions:
            for name_idx, name in enumerate(self.brief[question['id']]):
                row += 1

                if name_idx == 0:
                    assert sheet.read_cell(0, row) == question['name']
                else:
                    assert sheet.read_cell(0, row) == ''

                assert sheet.read_cell(1, row) == name

                for col, response in enumerate(self.responses):
                    assert sheet.read_cell(col + 2, row) == str(response[question['id']][name_idx]).lower()

    def test_populate_styled_ods_with_data_with_dynamic_list(self):
        questions = [
            {'id': 'niceToHaveRequirements', 'name': 'Nice-to-have skills & evidence', 'type': 'dynamic_list'},
            {'id': 'essentialRequirements', 'name': 'Essential skills & evidence', 'type': 'dynamic_list'},
        ]

        self.instance.get_questions = mock.Mock(return_value=[
            Question(question) for question in questions
        ])

        doc = self.instance.populate_styled_ods_with_data(self.instance.create_blank_ods_with_styles(),
                                                          {'brief': self.brief, 'responses': self.responses})

        sheet = doc.sheet("Supplier evidence")

        row = 0
        for question in questions:
            for name_idx, name in enumerate(self.brief[question['id']]):
                row += 1

                if name_idx == 0:
                    assert sheet.read_cell(0, row) == question['name']
                else:
                    assert sheet.read_cell(0, row) == ''

                assert sheet.read_cell(1, row) == name

                for col, response in enumerate(self.responses):
                    assert sheet.read_cell(col + 2, row) == response[question['id']][name_idx].get('evidence', '')

    def test_populate_styled_ods_with_data_missing_with_dynamic_list(self):
        questions = [
            {'id': 'niceToHaveRequirements', 'name': 'Nice-to-have skills & evidence', 'type': 'dynamic_list'},
            {'id': 'essentialRequirements', 'name': 'Essential skills & evidence', 'type': 'dynamic_list'},
        ]

        self.instance.get_questions = mock.Mock(return_value=[
            Question(question) for question in questions
        ])

        self.brief['niceToHaveRequirements'] = []

        del self.responses[0]['niceToHaveRequirements']
        del self.responses[1]['niceToHaveRequirements']

        doc = self.instance.populate_styled_ods_with_data(self.instance.create_blank_ods_with_styles(),
                                                          {'brief': self.brief, 'responses': self.responses})

        sheet = doc.sheet("Supplier evidence")

        k = 0

        for l, name in enumerate(self.brief['essentialRequirements']):
            k += 1

            for j, response in enumerate(self.responses):
                assert sheet.read_cell(j + 2, k) == response['essentialRequirements'][l].get('evidence', '')


@mock.patch("app.main.views.download_responses.data_api_client", autospec=True)
class TestDownloadBriefResponsesCsv(BaseApplicationTest):
    url = "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/responses/download"

    def setup_method(self, method):
        super(TestDownloadBriefResponsesCsv, self).setup_method(method)
        self.brief = BriefStub(status='closed').single_result_response()
        self.brief['briefs']['essentialRequirements'] = ["E1", "E2"]
        self.brief['briefs']['niceToHaveRequirements'] = ["Nice1", "Nice2", "Nice3"]

        self.brief_responses = {
            "briefResponses": [
                {
                    "supplierName": "Kev's Butties",
                    "availability": "Next Tuesday",
                    "dayRate": "£1.49",
                    "essentialRequirements": [True, True],
                    "niceToHaveRequirements": [True, False, False],
                    "respondToEmailAddress": "test1@email.com",
                },
                {
                    "supplierName": "Kev's Pies",
                    "availability": "A week Friday",
                    "dayRate": "£3.50",
                    "essentialRequirements": [True, True],
                    "niceToHaveRequirements": [False, True, True],
                    "respondToEmailAddress": "test2@email.com",
                },
                {
                    "supplierName": "Kev's Doughnuts",
                    "availability": "As soon as the sugar is delivered",
                    "dayRate": "£10 a dozen",
                    "essentialRequirements": [True, False],
                    "niceToHaveRequirements": [True, True, False],
                    "respondToEmailAddress": "test3@email.com",
                },
                {
                    "supplierName": "Kev's Fried Noodles",
                    "availability": "After Christmas",
                    "dayRate": "£12.35",
                    "essentialRequirements": [False, True],
                    "niceToHaveRequirements": [True, True, True],
                    "respondToEmailAddress": "test4@email.com",
                },
                {
                    "supplierName": "Kev's Pizza",
                    "availability": "Within the hour",
                    "dayRate": "£350",
                    "essentialRequirements": [False, False],
                    "niceToHaveRequirements": [False, False, False],
                    "respondToEmailAddress": "test5@email.com",
                },
            ]
        }

        self.tricky_character_responses = {
            "briefResponses": [
                {
                    "supplierName": "K,ev’s \"Bu,tties",
                    "availability": "❝Next — Tuesday❞",
                    "dayRate": "¥1.49,",
                    "essentialRequirements": [True, True],
                    "niceToHaveRequirements": [True, False, False],
                    "respondToEmailAddress": "test1@email.com",
                },
                {
                    "supplierName": "Kev\'s \'Pies",
                    "availability": "&quot;A week Friday&rdquot;",
                    "dayRate": "&euro;3.50",
                    "essentialRequirements": [True, True],
                    "niceToHaveRequirements": [False, True, True],
                    "respondToEmailAddress": "te,st2@email.com",
                },
            ]
        }

    @pytest.mark.parametrize('brief_status', download_responses.CLOSED_PUBLISHED_BRIEF_STATUSES)
    def test_csv_includes_all_eligible_responses_and_no_ineligible_responses(self, data_api_client, brief_status):
        self.brief['status'] = brief_status
        if brief_status == 'awarded':
            self.brief['awardedBriefResponseId'] = 999
        for framework_status in ['live', 'expired']:
            data_api_client.find_brief_responses.return_value = self.brief_responses
            data_api_client.get_framework.return_value = FrameworkStub(
                framework_slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            data_api_client.get_brief.return_value = self.brief

            self.login_as_buyer()
            res = self.client.get(self.url)
            page = res.get_data(as_text=True)
            lines = page.splitlines()
            # There are only the two eligible responses included
            assert len(lines) == 3
            assert lines[0] == (
                '''"Supplier","Date the specialist can start work","Day rate","Nice1","Nice2","Nice3","Email address"'''
            )
            # The response with two nice-to-haves is sorted to above the one with only one
            assert lines[1] == '''"Kev's Pies","A week Friday","£3.50","False","True","True","test2@email.com"'''
            assert lines[2] == '''"Kev's Butties","Next Tuesday","£1.49","True","False","False","test1@email.com"'''

    def test_download_brief_responses_for_brief_without_nice_to_haves(self, data_api_client):
        data_api_client.get_framework.return_value = FrameworkStub(
            framework_slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()

        for response in self.brief_responses['briefResponses']:
            del response["niceToHaveRequirements"]
        data_api_client.find_brief_responses.return_value = self.brief_responses

        data_api_client.get_brief.return_value = self.brief

        self.login_as_buyer()

        del self.brief['briefs']['niceToHaveRequirements']
        res = self.client.get(self.url)
        assert res.status_code, 200

        self.brief['briefs']['niceToHaveRequirements'] = []
        res = self.client.get(self.url)
        assert res.status_code, 200

    def test_csv_handles_tricky_characters(self, data_api_client):
        data_api_client.find_brief_responses.return_value = self.tricky_character_responses
        data_api_client.get_framework.return_value = FrameworkStub(
            framework_slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        data_api_client.get_brief.return_value = self.brief

        self.login_as_buyer()
        res = self.client.get(self.url)
        page = res.get_data(as_text=True)
        lines = page.splitlines()

        assert len(lines) == 3
        assert lines[0] == (
            '''"Supplier","Date the specialist can start work","Day rate","Nice1","Nice2","Nice3","Email address"'''
        )
        # The values with internal commas are surrounded by quotes, and all other characters appear as in the data
        assert lines[1] == '"Kev\'s \'Pies","&quot;A week Friday&rdquot;","&euro;3.50","False","True","True",' \
                           '"te,st2@email.com"'
        assert lines[2] == '"K,ev’s ""Bu,tties","❝Next — Tuesday❞","¥1.49,","True","False","False",' \
                           '"test1@email.com"'

    def test_404_if_brief_does_not_belong_to_buyer(self, data_api_client):
        data_api_client.get_framework.return_value = FrameworkStub(
            framework_slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        data_api_client.get_brief.return_value = BriefStub(user_id=234, status='closed').single_result_response()

        self.login_as_buyer()
        res = self.client.get(self.url)
        assert res.status_code == 404

    def test_404_if_brief_is_not_closed_or_awarded(self, data_api_client):
        data_api_client.get_framework.return_value = FrameworkStub(
            framework_slug='digital-outcomes-and-specialists',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()
        data_api_client.get_brief.return_value = BriefStub(status='live').single_result_response()

        self.login_as_buyer()
        res = self.client.get(self.url)
        assert res.status_code == 404

    def test_404_if_framework_is_not_live_or_expired(self, data_api_client):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
            data_api_client.get_framework.return_value = FrameworkStub(
                framework_slug='digital-outcomes-and-specialists',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()
            data_api_client.get_brief.return_value = BriefStub(status='closed').single_result_response()

            self.login_as_buyer()
            res = self.client.get(self.url)
            assert res.status_code == 404
