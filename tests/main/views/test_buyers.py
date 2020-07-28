# coding: utf-8
from __future__ import unicode_literals

from ...helpers import BaseApplicationTest
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub
import mock
from lxml import html
import pytest

from app.main.views import buyers


def find_briefs_mock():
    base_brief_values = {
        "createdAt": "2016-02-01T00:00:00.000000Z",
        "framework": {
            "slug": "digital-outcomes-and-specialists-4",
            "family": "digital-outcomes-and-specialists-4",
            "status": "live",
            "name": "Digital Outcomes and Specialists 4"
        },
        "frameworkSlug": "digital-outcomes-and-specialists-4",
        "lot": "digital-specialists"
    }

    find_briefs_response = {
        "briefs": [
            {
                "id": 20,
                "status": "draft",
                "title": "A draft brief"
            }, {
                "id": 21,
                "status": "live",
                "title": "A live brief",
                "publishedAt": "2016-02-04T12:00:00.000000Z"
            }, {
                "id": 22,
                "status": "closed",
                "title": "A closed brief with brief responses",
                "publishedAt": "2016-02-04T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-21T12:01:00.000000Z"
            }, {
                "id": 23,
                "status": "withdrawn",
                "title": "A withdrawn brief",
                "publishedAt": "2016-02-04T12:00:00.000000Z",
                "withdrawnAt": "2016-02-05T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-20T12:00:00.000000Z"
            }, {
                "id": 24,
                "status": "awarded",
                "title": "An awarded brief",
                "publishedAt": "2016-02-03T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-19T12:00:00.000000Z"
            }, {
                "id": 25,
                "status": "closed",
                "title": "A closed brief with no brief responses",
                "publishedAt": "2016-02-04T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-18T12:00:00.000000Z"
            },
            {
                "id": 26,
                "status": "cancelled",
                "title": "A cancelled brief",
                "publishedAt": "2016-02-04T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-17T12:00:00.000000Z"
            },
            {
                "id": 27,
                "status": "unsuccessful",
                "title": "An unsuccessful brief where no suitable suppliers applied",
                "publishedAt": "2016-02-04T12:00:00.000000Z",
                "applicationsClosedAt": "2016-02-16T12:00:00.000000Z"
            },
        ],
        "meta": {
            # let's imagine that this was just the first page of a bigger response
            "total": 44,
        },
    }

    for brief in find_briefs_response['briefs']:
        brief.update(base_brief_values)

    find_briefs_response["meta"] = {
        "total": len(find_briefs_response["briefs"]),
    }

    return find_briefs_response


class TestBuyerDashboard(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.find_briefs.return_value = find_briefs_mock()
        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_draft_briefs_section(self):
        res = self.client.get(self.briefs_dashboard_url)
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')

        assert res.status_code == 200

        draft_row = [cell.text_content().strip() for cell in tables[0].xpath('.//tbody/tr/td')]
        expected_link = '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/20'

        assert draft_row[0] == "A draft brief"
        assert tables[0].xpath('.//tbody/tr')[0].xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert draft_row[1] == "Monday 1 February 2016"

    def test_live_briefs_section(self):
        res = self.client.get(self.briefs_dashboard_url)
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')

        assert res.status_code == 200

        live_row = [cell.text_content().strip() for cell in tables[1].xpath('.//tbody/tr/td')]
        expected_link = '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/21'

        assert live_row[0] == "A live brief"
        assert tables[1].xpath('.//tbody/tr')[0].xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert live_row[1] == "Thursday 4 February 2016"

    def test_closed_briefs_section_with_closed_brief(self):
        res = self.client.get(self.briefs_dashboard_url)

        assert res.status_code == 200
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')
        closed_row_cells = tables[2].xpath('.//tbody/tr')[0].xpath('.//td')

        assert closed_row_cells[0].xpath('.//a')[0].text_content() == "A closed brief with brief responses"
        assert closed_row_cells[0].xpath('.//a/@href')[0] == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/22'

        assert tables[2].xpath('.//tbody/tr/td')[1].text_content().strip() == "Sunday 21 February 2016"

        assert closed_row_cells[2].xpath('.//a')[0].text_content() == "View responses"
        assert closed_row_cells[2].xpath('.//a/@href')[0] == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/22/responses'

        assert closed_row_cells[2].xpath('.//a')[1].text_content() == "Let suppliers know the outcome"
        assert closed_row_cells[2].xpath('.//a/@href')[1] == \
            '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/22/award'

    def test_closed_briefs_section_with_withdrawn_brief(self):
        res = self.client.get(self.briefs_dashboard_url)

        assert res.status_code == 200
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')
        withdrawn_row = tables[2].xpath('.//tbody/tr')[1]
        withdrawn_row_cells = [cell.text_content().strip() for cell in withdrawn_row.xpath('.//td')]
        expected_link = '/digital-outcomes-and-specialists-4/opportunities/23'

        assert withdrawn_row_cells[0] == "A withdrawn brief"
        assert withdrawn_row.xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert withdrawn_row_cells[1] == "Withdrawn"
        assert "View responses" not in withdrawn_row_cells[2]
        assert "Let suppliers know the outcome" not in withdrawn_row_cells[2]

    def test_closed_briefs_section_with_awarded_brief(self):
        res = self.client.get(self.briefs_dashboard_url)

        assert res.status_code == 200
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')
        awarded_row = tables[2].xpath('.//tbody/tr')[2]
        awarded_row_cells = [cell.text_content().strip() for cell in awarded_row.xpath('.//td')]
        expected_link = '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/24'

        assert awarded_row_cells[0] == "An awarded brief"
        assert awarded_row.xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert awarded_row_cells[1] == "Friday 19 February 2016"
        assert "View responses" not in awarded_row_cells[2]
        assert "Let suppliers know the outcome" not in awarded_row_cells[2]

    def test_closed_briefs_section_with_cancelled_brief(self):
        res = self.client.get(self.briefs_dashboard_url)

        assert res.status_code == 200
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')
        cancelled_row = tables[2].xpath('.//tbody/tr')[4]
        cancelled_row_cells = [cell.text_content().strip() for cell in cancelled_row.xpath('.//td')]
        expected_link = '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/26'

        assert cancelled_row_cells[0] == "A cancelled brief"
        assert cancelled_row.xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert cancelled_row_cells[1] == "Wednesday 17 February 2016"
        assert "View responses" not in cancelled_row_cells[2]
        assert "Let suppliers know the outcome" not in cancelled_row_cells[2]

    def test_closed_briefs_section_with_unsuccessful_brief(self):
        res = self.client.get(self.briefs_dashboard_url)

        assert res.status_code == 200
        tables = html.fromstring(res.get_data(as_text=True)).xpath('//table')
        unsuccessful_row = tables[2].xpath('.//tbody/tr')[5]
        unsuccessful_row_cells = [cell.text_content().strip() for cell in unsuccessful_row.xpath('.//td')]
        expected_link = '/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/27'

        assert unsuccessful_row_cells[0] == "An unsuccessful brief where no suitable suppliers applied"
        assert unsuccessful_row.xpath('.//td')[0].xpath('.//a/@href')[0] == expected_link
        assert unsuccessful_row_cells[1] == "Tuesday 16 February 2016"
        assert "View responses" not in unsuccessful_row_cells[2]
        assert "Let suppliers know the outcome" not in unsuccessful_row_cells[2]


class TestBuyerRoleRequired(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_login_required_for_buyer_pages(self):
        res = self.client.get(self.briefs_dashboard_url)
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login?next={}'.format(
            self.briefs_dashboard_url.replace('/', '%2F')
        )

    def test_supplier_cannot_access_buyer_pages(self):
        self.login_as_supplier()
        res = self.client.get(self.briefs_dashboard_url)
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login?next={}'.format(
            self.briefs_dashboard_url.replace('/', '%2F')
        )
        self.assert_flashes('You must log in with a buyer account to see this page.', expected_category='error')

    def test_buyer_pages_ok_if_logged_in_as_buyer(self):
        self.login_as_buyer()
        res = self.client.get(self.briefs_dashboard_url)
        page_text = res.get_data(as_text=True)

        assert res.status_code == 200
        assert 'Your requirements' in page_text


class AbstractViewBriefResponsesPage(BaseApplicationTest):
    framework_slug = "digital-outcomes-and-specialists-4"

    def setup_method(self, method):
        super().setup_method(method)

        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        framework = FrameworkStub(
            slug=self.framework_slug,
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=True).response(),
            ]
        ).single_result_response()
        self.data_api_client.get_framework.return_value = framework

        closed_brief_stub = BriefStub(
            framework_slug=self.framework_slug,
            lot_slug="digital-outcomes",
            status='closed',
            user_id=123,
        ).single_result_response()
        closed_brief_stub['briefs'].update({
            "framework": framework["frameworks"],
            "publishedAt": self.brief_publishing_date,
        })
        self.data_api_client.get_brief.return_value = closed_brief_stub

        self.data_api_client.find_brief_responses.return_value = self.brief_responses

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_page_shows_correct_content_when_eligible_responses(self):
        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )
        page = res.get_data(as_text=True)

        assert res.status_code == 200
        assert "Shortlist suppliers" in page
        assert "2 suppliers" in page
        assert "responded to your requirements and meet all your essential skills and experience." in page
        assert (
            "Any suppliers that did not meet all your essential requirements "
            "have already been told they were unsuccessful."
        ) in page

    @pytest.mark.parametrize('status', buyers.CLOSED_PUBLISHED_BRIEF_STATUSES)
    def test_page_visible_for_awarded_cancelled_unsuccessful_briefs(self, status):
        brief_stub = BriefStub(
            framework_slug=self.framework_slug,
            lot_slug="digital-outcomes",
            status="closed",
        ).single_result_response()
        brief_stub['briefs'].update(
            {
                'publishedAt': self.brief_publishing_date,
                'status': status
            }
        )
        if status == 'awarded':
            brief_stub['briefs']['awardedBriefResponseId'] = 999

        self.data_api_client.get_brief.return_value = brief_stub
        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )
        assert res.status_code == 200

    def test_page_does_not_pluralise_for_single_response(self):
        self.data_api_client.find_brief_responses.return_value = {
            "briefResponses": [self.brief_responses["briefResponses"][0]]
        }

        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )
        page = res.get_data(as_text=True)
        assert res.status_code == 200
        assert "1 supplier" in page
        assert "responded to your requirements and meets all your essential skills and experience." in page

    def test_404_if_brief_does_not_belong_to_buyer(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug=self.framework_slug,
            lot_slug="digital-outcomes",
            user_id=234,
        ).single_result_response()

        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )

        assert res.status_code == 404

    def test_404_if_brief_is_not_closed_or_awarded(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug=self.framework_slug,
            lot_slug="digital-outcomes",
            status="live",
        ).single_result_response()

        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )

        assert res.status_code == 404

    def test_404_if_lot_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug=self.framework_slug,
            status='live',
            lots=[
                LotStub(slug='digital-outcomes', allows_brief=False).response(),
            ]
        ).single_result_response()

        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )

        assert res.status_code == 404

    def test_404_if_brief_has_wrong_lot(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug=self.framework_slug,
            status='live',
            lots=[
                LotStub(slug='digital-specialists', allows_brief=True).response(),
            ]
        ).single_result_response()

        self.login_as_buyer()
        res = self.client.get(
            f"/buyers/frameworks/{self.framework_slug}/requirements/digital-outcomes/1234/responses"
        )

        assert res.status_code == 404


class TestViewBriefResponsesPageForLegacyBrief(AbstractViewBriefResponsesPage):
    brief_responses = {
        "briefResponses": [
            {"essentialRequirements": [True, True, True, True, True]},
            {"essentialRequirements": [True, False, True, True, True]},
            {"essentialRequirements": [True, True, False, False, True]},
            {"essentialRequirements": [True, True, True, True, True]},
            {"essentialRequirements": [True, True, True, True, False]},
        ]
    }

    brief_publishing_date = '2016-01-21T12:00:00.000000Z'

    framework_slug = "digital-outcomes-and-specialists"

    def test_page_shows_correct_message_for_legacy_brief_if_no_eligible_responses(self):
        self.data_api_client.find_brief_responses.return_value = {
            "briefResponses": [self.brief_responses["briefResponses"][1]]
        }

        self.login_as_buyer()
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-outcomes/1234/responses"
        )
        page = res.get_data(as_text=True)

        assert res.status_code == 200
        assert "There were no applications" in page
        assert "No suppliers met your essential skills and experience requirements." in page
        assert "All the suppliers who applied have already been told they were unsuccessful." in page

    def test_page_shows_csv_download_link(self):
        # Specify DOS 1 brief
        self.data_api_client.get_brief.return_value = BriefStub(
            lot_slug="digital-outcomes",
            status='closed',
            framework_slug='digital-outcomes-and-specialists',
            framework_name='Digital Outcomes and Specialists'
        ).single_result_response()

        self.login_as_buyer()
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-outcomes/1234/responses"
        )
        document = html.fromstring(res.get_data(as_text=True))
        csv_link = document.xpath(
            '//a[@href="/buyers/frameworks/digital-outcomes-and-specialists/requirements/digital-outcomes/1234/responses/download"]'  # noqa
        )[0]

        assert res.status_code == 200
        assert self._strip_whitespace(csv_link.text_content()) == \
            "Downloadsupplierresponsesto‘Ineedathingtodoathing’(CSV)"


class TestViewBriefResponsesPageForNewFlowBrief(AbstractViewBriefResponsesPage):
    brief_responses = {
        "briefResponses": [
            {"essentialRequirementsMet": True, "essentialRequirements": [{"evidence": "blah"}]},
            {"essentialRequirementsMet": True, "essentialRequirements": [{"evidence": "blah"}]},
        ]
    }

    brief_publishing_date = '2017-01-21T12:00:00.000000Z'

    def test_page_shows_correct_message_for_no_responses(self):
        self.data_api_client.find_brief_responses.return_value = {
            "briefResponses": []
        }

        self.login_as_buyer()
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/responses"
        )
        page = res.get_data(as_text=True)

        assert res.status_code == 200
        assert "There were no applications" in page
        assert "No suppliers met your essential skills and experience requirements." in page
        assert "All the suppliers who applied have already been told they were unsuccessful." not in page

    def test_page_shows_ods_download_link(self):
        brief_stub = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4",
            lot_slug="digital-outcomes",
            status="closed",
            user_id=123,
        ).single_result_response()

        brief_stub['briefs'].update({
            "framework": self.data_api_client.get_framework.return_value["frameworks"],
            "publishedAt": self.brief_publishing_date,
        })
        self.data_api_client.get_brief.return_value = brief_stub

        self.login_as_buyer()
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/responses"
        )
        document = html.fromstring(res.get_data(as_text=True))
        csv_link = document.xpath(
            '//a[@href="/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234/responses/download"]'  # noqa
        )[0]

        assert res.status_code == 200
        assert self._strip_whitespace(csv_link.text_content()) == \
            "Downloadsupplierresponsestothisrequirement(ODS)"


class TestBuyerAccountOverview(BaseApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("has_briefs", (False, True,))
    @pytest.mark.parametrize(
        ("projects_awaiting_outcomes", "all_projects"),
        (
            (0, 0),
            (0, 3),
            (24, 30),
        ),
    )
    def test_buyer_account_overview(self, has_briefs, projects_awaiting_outcomes, all_projects):
        def _find_direct_award_projects_mock_impl(
            user_id=None,
            having_outcome=None,
            locked=None,
            page=None,
            latest_first=None,
            with_users=False,
        ):
            assert user_id == 123
            if locked is True and having_outcome is False:
                return {
                    "projects": [
                        {
                            "id": project_id,
                            "name": "Poldy",
                            "lockedAt": "2010-11-12T13:14:15.12345Z",
                            "outcome": None,
                        } for project_id in range(321, 321 + min(projects_awaiting_outcomes, 5))
                        # limited to listing of 5 to simulate it being the first of a multi-page response
                    ],
                    "meta": {
                        "total": projects_awaiting_outcomes,
                    },
                }
            elif locked is None and having_outcome is None:
                return {
                    "projects": [
                        {
                            "id": project_id,
                            "name": "Poldy",
                            "lockedAt": "2010-11-12T13:14:15.12345Z" if project_id % 2 else None,
                            "outcome": {"id": project_id * 2} if project_id % 6 else None,
                        } for project_id in range(321, 321 + min(all_projects, 5))
                        # limited to listing of 5 to simulate it being the first of a multi-page response
                    ],
                    "meta": {
                        "total": all_projects,
                    },
                }
            raise AssertionError("unexpected argument combination")

        self.data_api_client.find_direct_award_projects.side_effect = _find_direct_award_projects_mock_impl
        self.data_api_client.find_briefs.return_value = find_briefs_mock() if has_briefs else {
            "briefs": [],
            "meta": {
                "total": 0,
            },
        }
        self.login_as_buyer()

        res = self.client.get('/buyers')
        assert res.status_code == 200

        document = html.fromstring(res.get_data())
        assert document.xpath("//h2[normalize-space(string())=$t]", t="Cloud hosting, software and support")
        assert document.xpath(
            "//h2[normalize-space(string())=$t]",
            t="Digital outcomes, specialists and user research participants",
        )
        assert document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="/user/change-password",
            t="Change your password",
        )
        assert document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            u="/user/cookie-settings",
            t="Change your cookie settings",
        )

        assert bool(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            t="View your requirements",
            u=self.briefs_dashboard_url,
        )) == has_briefs
        # but now also a broader assertion mainly aimed at the negative case
        assert bool(document.xpath(
            "/*[contains(normalize-space(string()), $t)]",
            t="View your requirements",
        )) == has_briefs
        assert bool(document.xpath(
            "/*[contains(normalize-space(string()), $t)]",
            t="You don't have any requirements.",
        )) == (not has_briefs)

        assert bool(document.xpath(
            "/*[contains(normalize-space(string()), $t)]",
            t="tell us the outcome",
        )) == bool(projects_awaiting_outcomes)
        assert bool(document.xpath(
            "/*[contains(normalize-space(string()), $t)]",
            t=f"outcome for {projects_awaiting_outcomes} saved search",
        )) == bool(projects_awaiting_outcomes)
        assert bool(document.xpath(
            "//a[@href=$u][normalize-space(string())=$t]",
            t="View your saved searches",
            u="/buyers/direct-award/g-cloud",
        )) == bool(all_projects)
        # but now also a broader assertion mainly aimed at the negative case
        assert bool(document.xpath(
            "/*[contains(normalize-space(string()), $t)]",
            t="View your saved searches",
        )) == bool(all_projects)
        assert bool(document.xpath(
            "//*[normalize-space(string())=$t]",
            t="You don't have any saved searches."
        )) == (not all_projects)

        assert self.data_api_client.find_direct_award_projects.called is True
