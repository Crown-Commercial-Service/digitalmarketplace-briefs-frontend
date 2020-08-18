import mock
import pytest
from lxml import html

from dmcontent.content_loader import ContentLoader
from dmtestutils.api_model_stubs import BriefStub, FrameworkStub, LotStub

from ...helpers import BaseApplicationTest


class BaseRequirementsTaskListPageTest:
    """Common tests for the create a brief journey's task list page

    Tests of things that should stay the same in all states.
    """

    task_list_selector = "ol.dm-task-list"
    task_list_section_selector = f"{task_list_selector} li.dm-task-list__section"
    task_list_item_selector = f"{task_list_section_selector} ul.dm-task-list__items > li.dm-task-list__item"
    task_list_tags_selector = f"{task_list_item_selector} strong.govuk-tag.dm-task-list__tag"
    task_list_link_selector = f"{task_list_section_selector} ul.govuk-list > li.dm-task-list__link"

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch("app.main.views.requirement_task_list.data_api_client", autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def get_requirements_task_list_page(self, brief: dict) -> html.HtmlElement:
        url = f"/buyers/frameworks/{brief['framework']['slug']}/requirements/{brief['lotSlug']}/{brief['id']}"
        res = self.client.get(url)

        assert res.status_code == 200, f"Cannot access requirements task list page for {brief['status']} brief at {url}"

        return html.fromstring(res.get_data(as_text=True))

    @pytest.fixture
    def requirements_task_list_page(self, brief) -> html.HtmlElement:
        return self.get_requirements_task_list_page(brief)

    @pytest.fixture
    def task_list_html(self, requirements_task_list_page) -> str:
        task_list = requirements_task_list_page.cssselect(self.task_list_selector)
        assert len(task_list) == 1
        return html.tostring(task_list[0]).decode()

    def test_can_view_requirements_task_list_page(self, brief):
        assert self.get_requirements_task_list_page(brief)

    def test_requirements_task_list_page_title_starts_with_brief_title(self, brief, requirements_task_list_page):
        page_title = requirements_task_list_page.find("head/title").text.strip()
        assert page_title.startswith(brief["title"])

    def test_requirements_task_list_page_heading_is_brief_title(self, brief, requirements_task_list_page):
        page_heading = requirements_task_list_page.cssselect("h1")[0].text_content()
        assert page_heading.strip() == brief["title"]

    def test_requirements_task_list_page_has_task_list(self, requirements_task_list_page):
        assert requirements_task_list_page.cssselect(self.task_list_selector)

    def test_task_list_has_sections(self, requirements_task_list_page):
        sections = requirements_task_list_page.cssselect(self.task_list_section_selector)
        headings = [section.cssselect("h2")[0] for section in sections]

        assert [h2.text_content().strip() for h2 in headings] == [
            "1. Write requirements",
            "2. Set how you’ll evaluate suppliers",
            "3. Publish requirements",
            "4. Answer supplier questions",
            "5. Shortlist",
            "6. Evaluate",
            "7. Award a contract",
        ]

    def test_task_list_items_have_tags(self, requirements_task_list_page):
        """Test that each item has a tag with allowed text"""
        tags = requirements_task_list_page.cssselect(self.task_list_tags_selector)

        allowed_tags = ("Done", "To do", "In progress", "Optional", "Cannot start yet")

        for tag in tags:
            assert tag.text in allowed_tags


class TestRequirementsTaskListPageDraftBrief(BaseRequirementsTaskListPageTest, BaseApplicationTest):
    """Test the requirements task list page when a brief is being drafted

    This should only possible with a live framework
    """

    @pytest.fixture(autouse=True)
    def brief(self):
        """A draft brief on a live framework"""
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status="live",
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status="draft",
        ).single_result_response()

        return self.data_api_client.get_brief.return_value["briefs"]

    def test_draft_brief_requirements_task_list(self, task_list_html, snapshot):
        assert task_list_html == snapshot

    def test_draft_brief_requirements_task_list_page_has_link_to_delete(self, brief, requirements_task_list_page):
        sidebar = requirements_task_list_page.cssselect("div.govuk-grid-column-one-third")[0]
        sidebar_links = sidebar.cssselect("a.govuk-link")
        assert len(sidebar_links) == 1

        delete_link = sidebar_links[0]
        assert delete_link.text == "Delete draft requirements"
        assert delete_link.attrib["href"] == (
            f"/buyers/frameworks/{brief['framework']['slug']}" f"/requirements/{brief['lotSlug']}/{brief['id']}/delete"
        )

    @pytest.mark.parametrize(
        "task_name, brief_data",
        [
            ("Specialist role", {"specialistRole": "communicationsManager"}),
            ("Location", {"location": "London"}),
            (
                "Description of work",
                {
                    "organisation": "Org Inc.",
                    "specialistWork": "Werk.",
                    "existingTeam": "Team members.",
                    "workplaceAddress": "Townsville",
                    "workingArrangements": "Arrangements.",
                    "startDate": "Tomorrow.",
                    "summary": "Summary.",
                },
            ),
            (
                "Shortlist and evaluation process",
                {
                    "numberOfSuppliers": 7,
                    "technicalWeighting": 60,
                    "culturalWeighting": 20,
                    "priceWeighting": 20,
                    "essentialRequirements": ["skills", "experience"],
                    "culturalFitCriteria": ["cultural", "fit"],
                },
            ),
            ("Set how long your requirements will be open for", {"requirementsLength": "1 week"},),
            ("Describe question and answer session", {"questionAndAnswerSessionDetails": "Q&A."},),
        ],
    )
    def test_draft_brief_requirements_task_list_tasks_show_when_done(self, brief, task_name, brief_data):
        document = self.get_requirements_task_list_page(brief)

        tag_selector = f".dm-task-list__task-name:contains('{task_name}') + .dm-task-list__tag"
        tag = document.cssselect(tag_selector)[0]

        assert tag.text.strip() in ["To do", "Optional"]

        brief.update(brief_data)

        document = self.get_requirements_task_list_page(brief)

        tag = document.cssselect(tag_selector)[0]

        assert tag.text.strip() == "Done"

        # Only the Title task and the task we've just completed should say done
        all_tags = document.cssselect(".dm-task-list__tag")
        assert len([tag for tag in all_tags if tag.text.strip() == "Done"]) == 2

    @pytest.mark.parametrize(
        "task_name, brief_data",
        [
            ("Description of work", {"organisation": "Org Inc."}),
            ("Description of work", {"specialistWork": "Werk."}),
            ("Description of work", {"existingTeam": "Team members."}),
            ("Description of work", {"workplaceAddress": "Townsville"}),
            ("Description of work", {"workingArrangements": "Arrangements."}),
            ("Description of work", {"startDate": "Tomorrow."}),
            ("Description of work", {"summary": "Summary."}),
            ("Shortlist and evaluation process", {"numberOfSuppliers": 7}),
            ("Shortlist and evaluation process", {"technicalWeighting": 60}),
            ("Shortlist and evaluation process", {"culturalWeighting": 20}),
            ("Shortlist and evaluation process", {"priceWeighting": 20}),
            ("Shortlist and evaluation process", {"essentialRequirements": ["skills", "experience"]},),
            ("Shortlist and evaluation process", {"culturalFitCriteria": ["cultural", "fit"]},),
        ],
    )
    def test_draft_brief_requirements_task_list_tasks_show_when_in_progress(self, brief, task_name, brief_data):
        document = self.get_requirements_task_list_page(brief)

        tag_selector = f".dm-task-list__task-name:contains('{task_name}') + .dm-task-list__tag"
        tag = document.cssselect(tag_selector)[0]

        assert tag.text.strip() == "To do"

        brief.update(brief_data)

        document = self.get_requirements_task_list_page(brief)

        tag = document.cssselect(tag_selector)[0]

        assert tag.text.strip() == "In progress"

        # Only the the task we've just started should say in progress
        all_tags = document.cssselect(".dm-task-list__tag")
        assert len([tag for tag in all_tags if tag.text.strip() == "In progress"]) == 1

    @pytest.mark.parametrize("lot_slug", ["digital-specialists", "digital-outcomes"])
    @pytest.mark.parametrize("task_name", ["Preview your requirements", "Publish your requirements"])
    def test_draft_brief_requirements_task_list_cannot_start_tasks(self, lot_slug, task_name):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status="live",
            lots=[LotStub(slug=lot_slug, allows_brief=True).response()],
        ).single_result_response()
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", lot_slug=lot_slug, status="draft",
        ).single_result_response()
        brief = self.data_api_client.get_brief.return_value["briefs"]

        document = self.get_requirements_task_list_page(brief)

        task_name_selector = f".dm-task-list__task-name:contains('{task_name}')"
        tag_selector = f"{task_name_selector} + .dm-task-list__tag"
        task_name = document.cssselect(task_name_selector)[0]
        tag = document.cssselect(tag_selector)[0]

        assert task_name.find("a") is None, "task should not be a link when it cannot be started"
        assert tag.text.strip() == "Cannot start yet"

        brief.update(
            {
                "specialistRole": "communicationsManager",
                "location": "London",
                "organisation": "Org Inc.",
                "specialistWork": "Werk.",
                "backgroundInformation": "Information.",
                "outcome": "Problem to be solved.",
                "endUsers": "Who the users are.",
                "phase": "Alpha",
                "existingTeam": "Team members.",
                "workplaceAddress": "Townsville",
                "workingArrangements": "Arrangements.",
                "startDate": "Tomorrow.",
                "summary": "Summary.",
                "numberOfSuppliers": 7,
                "technicalWeighting": 60,
                "culturalWeighting": 20,
                "priceWeighting": 20,
                "essentialRequirements": ["skills", "experience"],
                "culturalFitCriteria": ["cultural", "fit"],
                "successCriteria": ["proposal", "evaluation"],
                "priceCriteria": "fixedPrice",
                "requirementsLength": "1 week",
                "questionAndAnswerSessionDetails": "Q&A.",
            }
        )

        document = self.get_requirements_task_list_page(brief)

        task_name = document.cssselect(task_name_selector)[0]
        tag = document.cssselect(tag_selector)[0]

        assert tag.text.strip() in ["Optional", "To do"]
        assert task_name.find("a") is not None, "task should be a link when it can be started"

    @mock.patch("app.main.views.requirement_task_list.content_loader", autospec=True)
    def test_links_to_sections_go_to_the_correct_pages_whether_they_be_sections_or_questions(
        self, content_loader, brief
    ):  # noqa
        content_fixture = ContentLoader("tests/fixtures/content")
        content_fixture.load_manifest("dos", "data", "edit_brief")
        content_loader.get_manifest.return_value = content_fixture.get_manifest("dos", "edit_brief")

        document = self.get_requirements_task_list_page(brief)

        section_steps = document.cssselect("ol.dm-task-list")
        section_1_link = section_steps[0].xpath('li//a[contains(text(), "Section 1")]')
        section_2_link = section_steps[0].xpath('li//a[contains(text(), "Section 2")]')
        section_4_link = section_steps[0].xpath('li//a[contains(text(), "Section 4")]')

        # section with multiple questions
        assert (
            section_1_link[0].get("href").strip()
            == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-1"
        )
        # section with single question
        assert (
            section_2_link[0].get("href").strip() == "/buyers/frameworks/digital-outcomes-and-specialists-4"
            "/requirements/digital-specialists/1234/edit/section-2/required2"
        )
        # section with single question and a description
        assert (
            section_4_link[0].get("href").strip()
            == "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234/section-4"
        )


class TestRequirementsTaskListPageLiveBrief(BaseRequirementsTaskListPageTest, BaseApplicationTest):
    """Test a live brief (one which has been published)

    Live briefs can be on live or expired frameworks.
    """

    @pytest.fixture(autouse=True, params=["live", "expired"])
    def brief(self, request):
        """A live brief on a live or expired framework"""

        framework_status = request.param

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status=framework_status,
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status="live",
        ).single_result_response()

        brief_json["briefs"]["publishedAt"] = "2016-04-02T20:10:00.00000Z"
        brief_json["briefs"]["specialistRole"] = "communicationsManager"
        brief_json["briefs"]["clarificationQuestionsAreClosed"] = True

        self.data_api_client.get_brief.return_value = brief_json

        return brief_json["briefs"]

    def test_live_brief_requirements_task_list(self, task_list_html, snapshot):
        assert task_list_html == snapshot

    def test_live_brief_requirements_task_list_page_has_link_to_withdraw(self, brief, requirements_task_list_page):
        sidebar = requirements_task_list_page.cssselect("div.govuk-grid-column-one-third")[0]
        sidebar_links = sidebar.cssselect("a.govuk-link")
        assert len(sidebar_links) == 1

        withdraw_link = sidebar_links[0]
        assert withdraw_link.text == "Withdraw requirements"
        assert withdraw_link.attrib["href"] == (
            f"/buyers/frameworks/{brief['framework']['slug']}/requirements/{brief['lotSlug']}/{brief['id']}/withdraw"
        )


class TestRequirementsTaskListPageClosedBrief(BaseRequirementsTaskListPageTest, BaseApplicationTest):
    """Test closed briefs

    Closed briefs can be on live or expired frameworks.
    """

    @pytest.fixture(autouse=True, params=["live", "expired"])
    def brief(self, request):
        """A closed brief on a live or expired framework"""

        framework_status = request.param

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status=framework_status,
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status="closed",
        ).single_result_response()
        brief_json["briefs"]["publishedAt"] = "2016-04-02T20:10:00.00000Z"
        brief_json["briefs"]["specialistRole"] = "communicationsManager"
        brief_json["briefs"]["clarificationQuestionsAreClosed"] = True
        self.data_api_client.get_brief.return_value = brief_json

        return brief_json["briefs"]

    def test_closed_brief_requirements_task_list(self, task_list_html, snapshot):
        assert task_list_html == snapshot

    def test_closed_briefs_requirements_task_list_page_has_link_to_cancel(self, brief, requirements_task_list_page):
        sidebar = requirements_task_list_page.cssselect("div.govuk-grid-column-one-third")[0]
        sidebar_links = sidebar.cssselect("a.govuk-link")
        assert len(sidebar_links) == 1

        cancel_link = sidebar_links[0]
        assert cancel_link.text == "Cancel requirements"
        assert cancel_link.attrib["href"] == (
            f"/buyers/frameworks/{brief['framework']['slug']}" f"/requirements/{brief['lotSlug']}/{brief['id']}/cancel"
        )


class TestRequirementsTaskListPageCancelledOrUnsuccessfulBrief(BaseRequirementsTaskListPageTest, BaseApplicationTest):
    """Test briefs which were published and closed but had no successful responses"""

    @pytest.fixture(autouse=True, params=["live", "expired"])
    def framework(self, request):
        framework_status = request.param

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status=framework_status,
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        return self.data_api_client.get_framework.return_value["frameworks"]

    @pytest.fixture(autouse=True, params=["cancelled", "unsuccessful"])
    def brief(self, request):
        brief_status = request.param

        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status=brief_status,
        ).single_result_response()

        brief_json["briefs"]["publishedAt"] = "2016-04-02T20:10:00.00000Z"
        brief_json["briefs"]["specialistRole"] = "communicationsManager"
        brief_json["briefs"]["clarificationQuestionsAreClosed"] = True

        self.data_api_client.get_brief.return_value = brief_json

        return brief_json["briefs"]

    def test_cancelled_or_unsuccessful_brief_requirements_task_list(self, task_list_html, snapshot):
        assert task_list_html == snapshot


class TestRequirementsTaskListPageAwardedBrief(BaseRequirementsTaskListPageTest, BaseApplicationTest):
    """Test briefs which have been awarded"""

    @pytest.fixture(autouse=True, params=["live", "expired"])
    def brief(self, request):
        """An awarded brief on a live or expired framework"""

        framework_status = request.param

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status=framework_status,
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        brief_json = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status="awarded",
        ).single_result_response()

        brief_json["briefs"]["publishedAt"] = "2016-04-02T20:10:00.00000Z"
        brief_json["briefs"]["specialistRole"] = "communicationsManager"
        brief_json["briefs"]["clarificationQuestionsAreClosed"] = True
        brief_json["briefs"]["awardedBriefResponseId"] = 999

        self.data_api_client.get_brief.return_value = brief_json

        self.data_api_client.get_brief_response.return_value = {
            "briefResponses": {
                "awardDetails": {"awardedContractStartDate": "2016-4-4", "awardedContractValue": "100"},
                "id": 213,
                "status": "awarded",
                "supplierName": "100 Percent IT Ltd",
            }
        }

        return brief_json["briefs"]

    def test_awarded_brief_requirements_task_list(self, task_list_html, snapshot):
        assert task_list_html == snapshot

    def test_awarded_brief_requirements_task_list_page_checks_brief_responses(self, brief, requirements_task_list_page):
        assert self.data_api_client.get_brief_response.call_args_list == [mock.call(999)]

    def test_awarded_brief_requirements_task_list_page_includes_awarded_supplier(self, requirements_task_list_page):
        assert "Awarded to 100 Percent IT Ltd" in requirements_task_list_page.text_content()


class TestRequirementsTaskListPageAborts(BaseApplicationTest):
    """Test situations in which the requirements task list page does not work"""

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch("app.main.views.requirement_task_list.data_api_client", autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status="live",
            lots=[LotStub(slug="digital-specialists", allows_brief=True).response()],
        ).single_result_response()

        self.login_as_buyer()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_404_if_framework_does_not_allow_brief(self):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            slug="digital-outcomes-and-specialists-4",
            status="live",
            lots=[LotStub(slug="digital-specialists", allows_brief=False).response()],
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 404

    def test_404_if_brief_does_not_belong_to_user(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", user_id=234,
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 404

    def test_404_if_brief_has_wrong_lot(self):
        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-outcomes/1234"
        )

        assert res.status_code == 404

    def test_404_if_brief_is_withdrawn(self):
        self.data_api_client.get_brief.return_value = BriefStub(
            framework_slug="digital-outcomes-and-specialists-4", status="withdrawn",
        ).single_result_response()

        res = self.client.get(
            "/buyers/frameworks/digital-outcomes-and-specialists-4/requirements/digital-specialists/1234"
        )

        assert res.status_code == 404
