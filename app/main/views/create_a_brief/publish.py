from flask import abort, request, redirect, url_for
from flask_login import current_user

from dmcontent.html import to_summary_list_rows
from dmutils.dates import get_publishing_dates
from dmutils.flask import timed_render_template as render_template

from app import data_api_client
from ... import main, content_loader
from ...helpers.buyers_helpers import (
    brief_can_be_edited,
    count_unanswered_questions,
    get_framework_and_lot,
    is_brief_correct,
)


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/preview', methods=['GET'])
def preview_brief(framework_slug, lot_slug, brief_id):
    # Displays draft content in tabs for the user to see what their published brief will look like
    get_framework_and_lot(framework_slug, lot_slug, data_api_client, allowed_statuses=['live'], must_allow_brief=True)
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter({'lot': brief['lotSlug']})

    # Check that all questions have been answered
    unanswered_required, unanswered_optional = count_unanswered_questions(content.summary(brief))
    if unanswered_required > 0:
        return render_template(
            "buyers/preview_brief.html",
            content=content,
            unanswered_required=unanswered_required,
            brief=brief
        ), 400

    return render_template(
        "buyers/preview_brief.html",
        content=content,
        unanswered_required=unanswered_required,
        brief=brief
    ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/preview-source', methods=['GET'])
def preview_brief_source(framework_slug, lot_slug, brief_id):
    # This view's response currently is what will populate the iframes in the view above
    get_framework_and_lot(framework_slug, lot_slug, data_api_client, allowed_statuses=['live'], must_allow_brief=True)
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    # Check that all questions have been answered
    editable_content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter(
        {'lot': brief['lotSlug']}
    )
    unanswered_required, unanswered_optional = count_unanswered_questions(editable_content.summary(brief))
    if unanswered_required > 0:
        abort(400, 'There are still unanswered required questions')

    important_dates = get_publishing_dates(brief)

    display_content = content_loader.get_manifest(brief['frameworkSlug'], 'display_brief').filter(
        {'lot': brief['lotSlug']}
    )

    # Get attributes in format suitable for govukSummaryList
    brief_summary = display_content.summary(brief)
    for section in brief_summary:
        section.summary_list = to_summary_list_rows(
            section.questions,
            format_links=True,
            filter_empty=False,
            open_links_in_new_tab=True
        )

    # TODO: move preview_brief_source templates/includes into shared FE toolkit pattern to ensure it's kept in sync
    html = render_template(
        "buyers/preview_brief_source.html",
        content=display_content,
        content_summary=brief_summary,
        unanswered_required=unanswered_required,
        brief=brief,
        important_dates=important_dates
    )
    response_headers = {"X-Frame-Options": "sameorigin"}

    return html, 200, response_headers


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/publish', methods=['GET', 'POST'])
def publish_brief(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(framework_slug, lot_slug, data_api_client, allowed_statuses=['live'], must_allow_brief=True)
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter({'lot': brief['lotSlug']})
    brief_users = brief['users'][0]
    brief_user_name = brief_users['name']

    sections = content.summary(brief)
    question_and_answers = {}
    question_and_answers_content = sections.get_question('questionAndAnswerSessionDetails')
    question_and_answers['id'] = question_and_answers_content['id']

    # Annotate the section data with the section slug/id, to construct the Edit link in the template
    for section in sections:
        if section.get_question('questionAndAnswerSessionDetails') == question_and_answers_content:
            question_and_answers['slug'] = section['id']

    unanswered_required, unanswered_optional = count_unanswered_questions(sections)

    if request.method == 'POST':
        if unanswered_required > 0:
            abort(400, 'There are still unanswered required questions')
        data_api_client.publish_brief(brief_id, brief_user_name)
        return redirect(
            # the 'published' parameter is for tracking this request by analytics
            url_for('.view_brief_overview', framework_slug=brief['frameworkSlug'], lot_slug=brief['lotSlug'],
                    brief_id=brief['id'], published='true'))
    else:
        #  requirements length is a required question but is handled separately to other
        #  required questions on the publish page if it's unanswered.
        if (
            sections.get_section('set-how-long-your-requirements-will-be-open-for') and
            sections.get_section('set-how-long-your-requirements-will-be-open-for').questions[0].answer_required
        ):
            unanswered_required -= 1

        email_address = brief_users['emailAddress']
        dates = get_publishing_dates(brief)

        return render_template(
            "buyers/brief_publish_confirmation.html",
            email_address=email_address,
            question_and_answers=question_and_answers,
            unanswered_required=unanswered_required,
            sections=sections,
            brief=brief,
            dates=dates
        ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/timeline', methods=['GET'])
def view_brief_timeline(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]
    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or brief.get('status') != 'live':
        abort(404)

    dates = get_publishing_dates(brief)

    return render_template(
        "buyers/brief_publish_confirmation.html",
        email_address=brief['users'][0]['emailAddress'],
        published=True,
        brief=brief,
        dates=dates
    ), 200
