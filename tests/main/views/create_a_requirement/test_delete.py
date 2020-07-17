import mock

from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ....helpers import BaseApplicationTest


class TestDeleteBriefSubmission(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch(
            "app.main.views.create_a_requirement.delete.data_api_client", autospec=True
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

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_delete_brief_submission(self):
        for framework_status in ['live', 'expired']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists-4',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response()
                ]
            ).single_result_response()

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/delete"
            )

            assert res.status_code == 302
            assert self.data_api_client.delete_brief.called
            assert res.location == "http://localhost{}".format(self.briefs_dashboard_url)
            self.assert_flashes(
                "Your requirements ‘I need a thing to do a thing’ were deleted",
                expected_category="success"
            )

    def test_404_if_framework_is_not_live_or_expired(self):
        for framework_status in ['coming', 'open', 'pending', 'standstill']:
            self.data_api_client.get_framework.return_value = FrameworkStub(
                slug='digital-outcomes-and-specialists-4',
                status=framework_status,
                lots=[
                    LotStub(slug='digital-specialists', allows_brief=True).response()
                ]
            ).single_result_response()

            res = self.client.post(
                "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/delete",
            )
            assert res.status_code == 404
            assert not self.data_api_client.delete_brief.called

    def test_cannot_delete_live_brief(self):
        self.data_api_client.get_brief.return_value = BriefStub(status='live').single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/delete",
        )

        assert res.status_code == 404
        assert not self.data_api_client.delete_brief.called

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(user_id=234).single_result_response()

        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/"
            "digital-specialists/1234/delete",
            data={"delete_confirmed": True})

        assert res.status_code == 404

    def test_404_if_brief_has_wrong_lot(self):
        res = self.client.post(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/delete",
            data={"delete_confirmed": True})

        assert res.status_code == 404
