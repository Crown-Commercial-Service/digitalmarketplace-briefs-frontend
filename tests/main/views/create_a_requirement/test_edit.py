import mock
import pytest
from lxml import html

from dmcontent.content_loader import ContentLoader
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ....helpers import BaseApplicationTest


class TestEditBriefSubmission(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.edit.data_api_client", autospec=True
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

    def _test_breadcrumbs_on_question_page(self, response, has_summary_page=False, section_name=None, question=None):
        extra_breadcrumbs = [
            ('I need a thing to do a thing',
             '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234')
        ]
        if has_summary_page and section_name:
            extra_breadcrumbs.append(
                (
                    section_name, (
                        '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/' +
                        'digital-specialists/1234/{}'.format(section_name.lower().replace(' ', '-'))
                    )
                ),
            )
        if question:
            extra_breadcrumbs.append(
                (
                    question,
                )
            )

        self.assert_breadcrumbs(response, extra_breadcrumbs)

    def test_edit_brief_submission(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/description-of-work/organisation")

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Organisation the work is for"

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_edit_brief_submission_return_link_to_section_summary_if_section_has_description(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/section-4/optional2")

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        secondary_action_link = document.xpath('//a[normalize-space(text())="Return to section 4"]')[0]
        assert document.xpath('//h1')[0].text_content().strip() == "Optional 2"
        assert secondary_action_link.get('href').strip() == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-4"  # noqa
        self._test_breadcrumbs_on_question_page(
            response=res, has_summary_page=True, section_name='Section 4', question='Optional 2'
        )

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_edit_brief_submission_return_link_to_section_summary_if_other_questions(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/section-1/required1")

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        secondary_action_link = document.xpath('//a[normalize-space(text())="Return to section 1"]')[0]
        assert document.xpath('//h1')[0].text_content().strip() == "Required 1"
        assert secondary_action_link.get('href').strip() == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1"  # noqa
        self._test_breadcrumbs_on_question_page(
            response=res, has_summary_page=True, section_name='Section 1', question='Required 1'
        )

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_edit_brief_submission_return_link_to_brief_overview_if_single_question(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/section-2/required2")

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        secondary_action_link = document.xpath('//a[normalize-space(text())="Return to overview"]')[0]
        assert document.xpath('//h1')[0].text_content().strip() == "Required 2"
        assert secondary_action_link.get('href').strip() == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"  # noqa
        self._test_breadcrumbs_on_question_page(response=res, has_summary_page=False, question="Required 2")

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_edit_brief_submission_multiquestion(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/edit/section-5/required3")  # noqa

        assert res.status_code == 200

        document = html.fromstring(res.get_data(as_text=True))
        assert document.xpath('//h1')[0].text_content().strip() == "Required 3"
        assert document.xpath(
            '//*[@id="required3_1"]//span[contains(@class, "question-heading")]'
        )[0].text_content().strip() == "Required 3_1"
        assert document.xpath(
            '//*[@id="required3_2"]//span[contains(@class, "question-heading")]'
        )[0].text_content().strip() == "Required 3_2"

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(user_id=234).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/description-of-work/organisation")

        assert res.status_code == 404

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/description-of-work/organisation")

        assert res.status_code == 404

    def test_404_if_lot_does_not_exist(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-octopuses"
            "/1234/edit/description-of-work/organisation")

        assert res.status_code == 404

    def test_404_if_post_brief_has_wrong_lot(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-octopuses"
            "/1234/edit/description-of-work/organisation",
            data={"organisation": True}
        )

        assert res.status_code == 404

    def test_404_if_framework_status_is_not_live(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill', 'expired']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists-4',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response()
                ]
            ).single_result_response()

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
                "/1234/edit/description-of-work/organisation")

            assert res.status_code == 404

    def test_404_if_brief_has_published_status(self):
        self.data_api_client.get_brief.return_value = BriefStub(status='published').single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/description-of-work/organisation")

        assert res.status_code == 404

    def test_404_if_section_does_not_exist(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/not-a-real-section")

        assert res.status_code == 404

    def test_404_if_question_does_not_exist(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists"
            "/1234/edit/description-of-work/not-a-real-question")

        assert res.status_code == 404


class TestUpdateBriefSubmission(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.edit.data_api_client", autospec=True
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

    def test_update_brief_submission(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/organisation",
            data={
                "organisation": "GDS"
            })

        assert res.status_code == 302
        self.data_api_client.update_brief.assert_called_with(
            '1234',
            {"organisation": "GDS"},
            page_questions=['organisation'],
            updated_by='buyer@email.com'
        )

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_post_update_if_multiple_questions_redirects_to_section_summary(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/section-1/required1",
            data={
                "required1": True
            })

        assert res.status_code == 302
        self.data_api_client.update_brief.assert_called_with(
            '1234',
            {"required1": True},
            page_questions=['required1'],
            updated_by='buyer@email.com'
        )
        assert res.headers['Location'].endswith(
            'buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1'
        ) is True

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_post_update_if_section_description_redirects_to_section_summary(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/section-4/optional2",
            data={
                "optional2": True
            })

        assert res.status_code == 302
        self.data_api_client.update_brief.assert_called_with(
            '1234',
            {"optional2": True},
            page_questions=['optional2'],
            updated_by='buyer@email.com'
        )
        assert res.headers['Location'].endswith(
            'buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-4'
        ) is True

    @mock.patch("app.main.views.create_a_requirement.edit.content_loader", autospec=True)
    def test_post_update_if_single_question_no_description_redirects_to_overview(self, content_loader):
        content_fixture = ContentLoader('tests/fixtures/content')
        content_fixture.load_manifest('dos', 'data', 'edit_brief')
        content_loader.get_manifest.return_value = content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/section-2/required2",
            data={
                "required2": True
            })

        assert res.status_code == 302
        self.data_api_client.update_brief.assert_called_with(
            '1234',
            {"required2": True},
            page_questions=['required2'],
            updated_by='buyer@email.com'
        )
        assert res.headers['Location'].endswith(
            'buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234'
        ) is True

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(user_id=234).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/organisation",
            data={
                "organisation": "GDS"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/organisation",
            data={
                "title": "A new title"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_lot_does_not_exist(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-octopuses/1234/edit/description-of-work/organisation",
            data={
                "title": "A new title"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    @pytest.mark.parametrize('framework_status', ['coming', 'open', 'pending', 'standstill', 'expired'])
    def test_404_if_framework_status_is_not_live(self, framework_status):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status=framework_status,
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/organisation",
            data={
                "title": "A new title"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_brief_is_already_live(self):
        self.data_api_client.get_brief.return_value = BriefStub(status='live').single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/organisation",
            data={
                "title": "A new title"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called

    def test_404_if_question_does_not_exist(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/edit/description-of-work/some-made-up-question",
            data={
                "title": "A new title"
            })

        assert res.status_code == 404
        assert not self.data_api_client.update_brief.called


class TestViewBriefSectionSummaryPage(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.edit.data_api_client", autospec=True
        )
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

        self.content_fixture = ContentLoader('tests/fixtures/content')
        self.content_fixture.load_manifest('dos', 'data', 'edit_brief')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def _setup_brief(self, brief_status="draft", **stub_kwargs):
        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            status=brief_status,
            **stub_kwargs
        ).single_result_response()
        brief_questions = brief_json['briefs']
        brief_questions.update({
            'required1': 'test background info',
            'required2': 'work work work',
            'required3_1': 'yep',
            'required3_2': 'yep'
        })
        return brief_json

    @mock.patch('app.main.views.create_a_requirement.edit.content_loader', autospec=True)
    def test_get_view_section_summary(self, content_loader):
        content_loader.get_manifest.return_value = self.content_fixture.get_manifest('dos', 'edit_brief')

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1"
        )

        assert res.status_code == 200

    @pytest.mark.parametrize('show_dos_preview_links', (True, False, None))
    @mock.patch('app.main.views.create_a_requirement.edit.content_loader', autospec=True)
    def test_get_view_section_summary_links(self, content_loader, show_dos_preview_links):
        content_loader.get_manifest.return_value = self.content_fixture.get_manifest('dos', 'edit_brief')
        brief = self._setup_brief(lot_slug='digital-specialists')
        self.data_api_client.get_brief.return_value = brief

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1"
        )

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))

        overview_links = document.xpath(
            '//a[@href="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"]'
        )
        assert [link.text_content().strip() for link in overview_links] == [
            "I need a thing to do a thing",  # breadcrumbs
            "Return to overview"             # bottom nav link
        ]
        assert document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/preview",
            t="Preview your requirements",
        )

    def test_wrong_lot_get_view_section_summary(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/section-1"
        )

        assert res.status_code == 404
