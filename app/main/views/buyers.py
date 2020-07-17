# coding: utf-8
from __future__ import unicode_literals

from flask import abort, request, redirect, url_for, flash
from flask_login import current_user

from app import data_api_client
from .. import main, content_loader
from ..helpers.buyers_helpers import (
    add_unanswered_counts_to_briefs,
    brief_can_be_edited,
    count_unanswered_questions,
    get_framework_and_lot,
    is_brief_correct,
    is_legacy_brief_response,
    section_has_at_least_one_required_question,
)

from dmapiclient import HTTPError
from dmutils.flask import timed_render_template as render_template
from dmutils.formats import DATETIME_FORMAT
from dmutils.forms.errors import govuk_errors
from datetime import datetime

from collections import Counter

CLOSED_BRIEF_STATUSES = ['closed', 'withdrawn', 'awarded', 'cancelled', 'unsuccessful']
CLOSED_PUBLISHED_BRIEF_STATUSES = ['closed', 'awarded', 'cancelled', 'unsuccessful']

BRIEF_DELETED_MESSAGE = "Your requirements ‘{brief[title]}’ were deleted"
BRIEF_WITHDRAWN_MESSAGE = "You’ve withdrawn your requirements for ‘{brief[title]}’"


@main.route('')
def buyer_dashboard():
    user_projects_awaiting_outcomes_total = data_api_client.find_direct_award_projects(
        current_user.id,
        locked=True,
        having_outcome=False,
    )["meta"]["total"]

    return render_template(
        'buyers/index.html',
        user_briefs_total=data_api_client.find_briefs(current_user.id)["meta"]["total"],
        user_projects_awaiting_outcomes_total=user_projects_awaiting_outcomes_total,
        # calculating it this way allows us to avoid the extra api call if we already know the user has projects
        # from user_projects_awaiting_outcomes_total
        user_has_projects=bool(
            user_projects_awaiting_outcomes_total
            or data_api_client.find_direct_award_projects(current_user.id)["meta"]["total"]
        ),
    )


@main.route('/requirements/digital-outcomes-and-specialists')
def buyer_dos_requirements():
    user_briefs = data_api_client.find_briefs(current_user.id).get('briefs', [])

    draft_briefs = sorted(
        add_unanswered_counts_to_briefs([brief for brief in user_briefs if brief['status'] == 'draft'], content_loader),
        key=lambda i: datetime.strptime(i['createdAt'], DATETIME_FORMAT),
        reverse=True
    )
    live_briefs = sorted(
        [brief for brief in user_briefs if brief['status'] == 'live'],
        key=lambda i: datetime.strptime(i['publishedAt'], DATETIME_FORMAT),
        reverse=True
    )
    closed_briefs = sorted(
        [brief for brief in user_briefs if brief['status'] in CLOSED_BRIEF_STATUSES],
        key=lambda i: datetime.strptime(i['applicationsClosedAt'], DATETIME_FORMAT),
        reverse=True
    )

    return render_template(
        'buyers/dashboard.html',
        draft_briefs=draft_briefs,
        live_briefs=live_briefs,
        closed_briefs=closed_briefs,
    )


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>', methods=['GET'])
def view_brief_overview(framework_slug, lot_slug, brief_id):
    framework, lot = get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id):
        abort(404)

    awarded_brief_response_supplier_name = ""
    if brief.get('awardedBriefResponseId'):
        awarded_brief_response_supplier_name = data_api_client.get_brief_response(
            brief['awardedBriefResponseId'])["briefResponses"]["supplierName"]

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter({'lot': brief['lotSlug']})
    sections = content.summary(brief)
    delete_requested = request.args.get('delete_requested') and brief['status'] == 'draft'
    withdraw_requested = request.args.get('withdraw_requested') and brief['status'] == 'live'

    content_loader.load_messages(brief['frameworkSlug'], ['urls'])
    call_off_contract_url = content_loader.get_message(brief['frameworkSlug'], 'urls', 'call_off_contract_url')
    framework_agreement_url = content_loader.get_message(brief['frameworkSlug'], 'urls', 'framework_agreement_url')

    completed_sections = {}
    for section in sections:
        required, optional = count_unanswered_questions([section])
        if section_has_at_least_one_required_question(section):
            completed_sections[section.slug] = True if required == 0 else False
        else:
            completed_sections[section.slug] = True if optional == 0 else False

    brief['clarificationQuestions'] = [
        dict(question, number=index + 1)
        for index, question in enumerate(brief['clarificationQuestions'])
    ]

    publish_requirements_section_links = [
        {
            'href': url_for(
                ".preview_brief",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']
            ),
            'text': 'Preview your requirements',
            'allowed_statuses': ['draft']
        },
        {
            'href': url_for(
                ".publish_brief",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']
            ),
            'text': 'Publish your requirements',
            'allowed_statuses': ['draft']
        },
        {
            'href': url_for(
                ".view_brief_timeline",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']
            ),
            'text': 'View question and answer dates',
            'allowed_statuses': ['live']
        },
        {
            'href': url_for(
                "external.get_brief_by_id",
                framework_family=brief['framework']['family'],
                brief_id=brief['id']
            ),
            'text': 'View your published requirements',
            'allowed_statuses': ['live', 'closed', 'awarded', 'cancelled', 'unsuccessful']
        }
    ]

    return render_template(
        "buyers/brief_overview.html",
        framework=framework,
        confirm_remove=request.args.get("confirm_remove", None),
        brief=section.unformat_data(brief),
        sections=sections,
        completed_sections=completed_sections,
        step_sections=[section.step for section in sections if hasattr(section, 'step')],
        delete_requested=delete_requested,
        withdraw_requested=withdraw_requested,
        call_off_contract_url=call_off_contract_url,
        framework_agreement_url=framework_agreement_url,
        awarded_brief_response_supplier_name=awarded_brief_response_supplier_name,
        publish_requirements_section_links=publish_requirements_section_links
    ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/<section_slug>', methods=['GET'])
def view_brief_section_summary(framework_slug, lot_slug, brief_id, section_slug):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter({'lot': brief['lotSlug']})
    sections = content.summary(brief)
    section = sections.get_section(section_slug)

    if not section:
        abort(404)

    # Show preview link if all mandatory questions have been answered
    unanswered_required, unanswered_optional = count_unanswered_questions(sections)
    show_dos_preview_link = (unanswered_required == 0)

    return render_template(
        "buyers/section_summary.html",
        brief=brief,
        section=section,
        show_dos_preview_link=show_dos_preview_link
    ), 200


@main.route(
    '/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/edit/<section_slug>/<question_id>',
    methods=['GET'])
def edit_brief_question(framework_slug, lot_slug, brief_id, section_slug, question_id):
    get_framework_and_lot(framework_slug, lot_slug, data_api_client, allowed_statuses=['live'], must_allow_brief=True)
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter(
        {'lot': brief['lotSlug']}
    )
    section = content.get_section(section_slug)
    if section is None or not section.editable:
        abort(404)

    question = section.get_question(question_id)
    if not question:
        abort(404)

    return render_template(
        "buyers/edit_brief_question.html",
        brief=section.unformat_data(brief),
        section=section,
        question=question
    ), 200


@main.route(
    '/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/edit/<section_id>/<question_id>',
    methods=['POST'])
def update_brief_submission(framework_slug, lot_slug, brief_id, section_id, question_id):
    get_framework_and_lot(framework_slug, lot_slug, data_api_client, allowed_statuses=['live'], must_allow_brief=True)
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], 'edit_brief').filter({'lot': brief['lotSlug']})
    section = content.get_section(section_id)
    if section is None or not section.editable:
        abort(404)

    question = section.get_question(question_id)
    if not question:
        abort(404)

    update_data = question.get_data(request.form)

    try:
        data_api_client.update_brief(
            brief_id,
            update_data,
            updated_by=current_user.email_address,
            page_questions=question.form_fields
        )
    except HTTPError as e:
        update_data = section.unformat_data(update_data)
        errors = govuk_errors(section.get_error_messages(e.message))

        # we need the brief_id to build breadcrumbs and the update_data to fill in the form.
        brief.update(update_data)

        return render_template(
            "buyers/edit_brief_question.html",
            brief=brief,
            section=section,
            question=question,
            errors=errors
        ), 400

    if section.has_summary_page:
        return redirect(
            url_for(
                ".view_brief_section_summary",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id'],
                section_slug=section.slug)
        )

    return redirect(
        url_for(
            ".view_brief_overview",
            framework_slug=brief['frameworkSlug'],
            lot_slug=brief['lotSlug'],
            brief_id=brief['id']
        )
    )


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/responses', methods=['GET'])
def view_brief_responses(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True,
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(
        brief, framework_slug, lot_slug, current_user.id, allowed_statuses=CLOSED_PUBLISHED_BRIEF_STATUSES
    ):
        abort(404)

    brief_responses = data_api_client.find_brief_responses(brief_id)['briefResponses']

    brief_responses_required_evidence = (
        None
        if not brief_responses else
        not is_legacy_brief_response(brief_responses[0], brief=brief)
    )

    counter = Counter()

    for response in brief_responses:
        counter[all(response['essentialRequirements'])] += 1

    return render_template(
        "buyers/brief_responses.html",
        response_counts={"failed": counter[False], "eligible": counter[True]},
        brief_responses_required_evidence=brief_responses_required_evidence,
        brief=brief
    ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/delete', methods=['POST'])
def delete_a_brief(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    data_api_client.delete_brief(brief_id, current_user.email_address)
    flash(BRIEF_DELETED_MESSAGE.format(brief=brief), "success")

    return redirect(url_for(".buyer_dos_requirements"))


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/withdraw', methods=['POST'])
def withdraw_a_brief(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id, allowed_statuses=['live']):
        abort(404)

    data_api_client.withdraw_brief(brief_id, current_user.email_address)
    flash(BRIEF_WITHDRAWN_MESSAGE.format(brief=brief), "success")

    return redirect(url_for(".buyer_dos_requirements"))
