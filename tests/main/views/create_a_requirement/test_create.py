import mock
from lxml import html

from dmapiclient import HTTPError
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ....helpers import BaseApplicationTest


class TestStartNewBrief(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.login_as_buyer()
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.create.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_show_start_brief_page(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create")

        assert res.status_code == 200

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create")

        assert res.status_code == 404

    def test_404_if_framework_status_is_not_live(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill', 'expired']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists-4',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response(),
                ]
            ).single_result_response()

            res = self.client.get(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create")

            assert res.status_code == 404

    def test_404_if_lot_does_not_exist(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-octopuses/create")

        assert res.status_code == 404


class TestCreateNewBrief(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.create.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_create_new_digital_specialists_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create",
            data={
                "title": "Title"
            })

        assert res.status_code == 302
        self.data_api_client.create_brief.assert_called_with(
            'digital-outcomes-and-specialists-4',
            'digital-specialists',
            123,
            {'title': "Title"},
            page_questions=['title'],
            updated_by='buyer@email.com'
        )

    def test_create_new_digital_outcomes_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/create",
            data={
                "title": "Title"
            })

        assert res.status_code == 302
        self.data_api_client.create_brief.assert_called_with(
            'digital-outcomes-and-specialists-4',
            'digital-outcomes',
            123,
            {'title': "Title"},
            page_questions=['title'],
            updated_by='buyer@email.com'
        )

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='open',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=False).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create",
            data={
                "specialistRole": "agileCoach"
            })

        assert res.status_code == 404
        assert not self.data_api_client.create_brief.called

    def test_404_if_framework_status_is_not_live(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='open',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create",
            data={
                "specialistRole": "agileCoach"
            })

        assert res.status_code == 404
        assert not self.data_api_client.create_brief.called

    def test_404_if_lot_does_not_exist(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='open',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-octopuses/create",
            data={
                "specialistRole": "agileCoach"
            })

        assert res.status_code == 404
        assert not self.data_api_client.create_brief.called

    def test_400_if_form_error(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug='digital-outcomes-and-specialists-4',
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response()
            ]
        ).single_result_response()
        self.data_api_client.create_brief.side_effect = HTTPError(
            mock.Mock(status_code=400),
            {"title": "answer_required"})

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/create",
            data={
                "title": "Title"
            })
        document = html.fromstring(res.get_data(as_text=True))

        assert res.status_code == 400
        anchor = document.cssselect('div.govuk-error-summary a')

        assert len(anchor) == 1  # check that the framework iteration rendered a specific error message
        self.data_api_client.create_brief.assert_called_with(
            'digital-outcomes-and-specialists-4',
            'digital-specialists',
            123,
            {'title': "Title"},
            page_questions=['title'],
            updated_by='buyer@email.com'
        )


class TestCopyBrief(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.login_as_buyer()
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.create.data_api_client", autospec=True
        )
        self.data_api_client = self.data_api_client_patch.start()

        self.brief = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            framework_name="Digital Outcomes and Specialists 4"
        ).single_result_response()
        self.data_api_client.get_brief.return_value = self.brief

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_get_not_allowed(self):
        res = self.client.get(
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/copy'
        )

        assert res.status_code == 404

    def test_copy_brief_and_redirect_to_copied_brief_edit_title_page(self):
        new_brief = self.brief.copy()
        new_brief["briefs"]["id"] = 1235
        self.data_api_client.copy_brief.return_value = new_brief

        res = self.client.post(
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/copy'
        )

        self.data_api_client.copy_brief.assert_called_once_with('1234', 'buyer@email.com')

        assert res.location == (
            "http://localhost/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/"
            "1235/edit/title/title"
        )

    def test_copy_brief_for_expired_framework_redirects_to_edit_page_for_new_framework(self):
        self.data_api_client.get_brief.return_value = BriefStub().single_result_response()  # dos1 brief

        new_brief = self.brief.copy()  # dos4 brief
        new_brief["briefs"]["id"] = 1235
        self.data_api_client.copy_brief.return_value = new_brief

        res = self.client.post(
            '/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-specialists/1234/copy'
        )

        assert res.location == (
            "http://localhost/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/"
            "1235/edit/title/title"
        )

    @mock.patch("app.main.views.create_a_requirement.create.is_brief_correct", autospec=True)
    def test_404_if_brief_is_not_correct(self, is_brief_correct):
        is_brief_correct.return_value = False

        res = self.client.post(
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/copy'
        )

        assert res.status_code == 404
        is_brief_correct.assert_called_once_with(
            self.brief["briefs"],
            "digital-outcomes-and-specialists-4",
            "digital-specialists",
            123,
            allow_withdrawn=True
        )

    def test_can_copy_withdrawn_brief(self):
        # Make our original brief withdrawn
        withdrawn_brief = self.brief.copy()
        withdrawn_brief["briefs"].update({'status': 'withdrawn'})
        self.data_api_client.get_brief.return_value = withdrawn_brief

        # Set copied brief return
        new_brief = self.brief.copy()  # dos2 brief
        new_brief["briefs"]["id"] = 1235
        self.data_api_client.copy_brief.return_value = new_brief

        res = self.client.post(
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/copy'
        )

        # Assert redirect and copy_brief call
        assert res.status_code == 302
        self.data_api_client.copy_brief.assert_called_once_with('1234', 'buyer@email.com')
