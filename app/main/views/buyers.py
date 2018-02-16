# coding: utf-8
from __future__ import unicode_literals
import inflection
import flask_featureflags


from flask import abort, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user

from app import data_api_client
from .. import main, content_loader
from ..helpers.buyers_helpers import (
    get_framework_and_lot, get_sorted_responses_for_brief, count_unanswered_questions,
    brief_can_be_edited, add_unanswered_counts_to_briefs, is_brief_correct,
    section_has_at_least_one_required_question, get_briefs_breadcrumbs
)

from ..forms.awards import AwardedBriefResponseForm
from ..forms.cancel import CancelBriefForm
from ..forms.award_or_cancel import AwardOrCancelBriefForm


from dmapiclient import HTTPError
from dmutils.dates import get_publishing_dates
from dmutils.formats import DATETIME_FORMAT
from dmutils.views import DownloadFileView
from datetime import datetime

from collections import Counter

CLOSED_BRIEF_STATUSES = ['closed', 'withdrawn', 'awarded', 'cancelled', 'unsuccessful']
CLOSED_PUBLISHED_BRIEF_STATUSES = ['closed', 'awarded', 'cancelled', 'unsuccessful']

BRIEF_UPDATED_MESSAGE = "You've updated '{brief[title]}'"
BRIEF_DELETED_MESSAGE = "Your requirements ‘{brief[title]}’ were deleted"
BRIEF_WITHDRAWN_MESSAGE = "You've withdrawn your requirements for ‘{brief[title]}’"


@main.route('')
def buyer_dashboard():
    if flask_featureflags.is_active('DIRECT_AWARD_PROJECTS'):
        user_briefs_total = len(data_api_client.find_briefs(current_user.id).get('briefs', []))
        user_projects_total = len(data_api_client.find_direct_award_projects(current_user.id).get('projects', []))

        return render_template(
            'buyers/index.html',
            user_briefs_total=user_briefs_total,
            user_projects_total=user_projects_total
        )

    else:
        return buyer_dos_requirements()


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

    breadcrumbs = [
        {
            "link": "/",
            "label": "Digital Marketplace"
        }
    ]

    if flask_featureflags.is_active('DIRECT_AWARD_PROJECTS'):
        breadcrumbs += [
            {
                "link": url_for("buyers.buyer_dashboard"),
                "label": "Your account"
            }
        ]

    return render_template(
        'buyers/dashboard.html',
        draft_briefs=draft_briefs,
        live_briefs=live_briefs,
        closed_briefs=closed_briefs,
        breadcrumbs=breadcrumbs,
    )


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/create', methods=['GET'])
def start_new_brief(framework_slug, lot_slug):

    framework, lot = get_framework_and_lot(framework_slug, lot_slug, data_api_client,
                                           allowed_statuses=['live'], must_allow_brief=True)

    content = content_loader.get_manifest(framework_slug, 'edit_brief').filter(
        {'lot': lot['slug']}
    )

    section = content.get_section(content.get_next_editable_section_id())

    return render_template(
        "buyers/create_brief_question.html",
        brief={},
        framework=framework,
        lot=lot,
        section=section,
        question=section.questions[0],
    ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/create', methods=['POST'])
def create_new_brief(framework_slug, lot_slug):

    framework, lot = get_framework_and_lot(framework_slug, lot_slug, data_api_client,
                                           allowed_statuses=['live'], must_allow_brief=True)

    content = content_loader.get_manifest(framework_slug, 'edit_brief').filter(
        {'lot': lot['slug']}
    )

    section = content.get_section(content.get_next_editable_section_id())

    update_data = section.get_data(request.form)

    try:
        brief = data_api_client.create_brief(
            framework_slug,
            lot_slug,
            current_user.id,
            update_data,
            updated_by=current_user.email_address,
            page_questions=section.get_field_names()
        )["briefs"]
    except HTTPError as e:
        update_data = section.unformat_data(update_data)
        errors = section.get_error_messages(e.message)

        return render_template(
            "buyers/create_brief_question.html",
            data=update_data,
            brief={},
            framework=framework,
            lot=lot,
            section=section,
            question=section.questions[0],
            errors=errors
        ), 400

    return redirect(
        url_for(".view_brief_overview",
                framework_slug=framework_slug,
                lot_slug=lot_slug,
                brief_id=brief['id']))


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/copy', methods=['POST'])
def copy_brief(framework_slug, lot_slug, brief_id):
    brief = data_api_client.get_brief(brief_id)["briefs"]
    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id, allow_withdrawn=True):
        abort(404)

    new_brief = data_api_client.copy_brief(brief_id, current_user.email_address)['briefs']

    # Get first question for 'edit_brief'
    content = content_loader.get_manifest(framework_slug, 'edit_brief').filter(
        {'lot': lot_slug}
    )
    section = content.get_section(content.get_next_editable_section_id())

    # Redirect to first question with new (copy of) brief
    return redirect(url_for(
        '.edit_brief_question',
        framework_slug=new_brief["frameworkSlug"],
        lot_slug=new_brief["lotSlug"],
        brief_id=new_brief["id"],
        section_slug=section.slug,
        question_id=section.questions[0].id
    ))


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

    breadcrumbs = get_briefs_breadcrumbs()

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
        breadcrumbs=breadcrumbs
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

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    return render_template(
        "buyers/section_summary.html",
        brief=brief,
        section=section,
        breadcrumbs=breadcrumbs,
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

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    return render_template(
        "buyers/edit_brief_question.html",
        brief=section.unformat_data(brief),
        section=section,
        question=question,
        breadcrumbs=breadcrumbs,
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
        errors = section.get_error_messages(e.message)

        # we need the brief_id to build breadcrumbs and the update_data to fill in the form.
        brief.update(update_data)

        breadcrumbs = get_briefs_breadcrumbs([
            {
                "link": url_for(
                    ".view_brief_overview",
                    framework_slug=brief['frameworkSlug'],
                    lot_slug=brief['lotSlug'],
                    brief_id=brief['id']),
                "label": brief['title']
            }
        ])

        return render_template(
            "buyers/edit_brief_question.html",
            brief=brief,
            section=section,
            question=question,
            errors=errors,
            breadcrumbs=breadcrumbs,
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

    brief_responses_require_evidence = (
        datetime.strptime(current_app.config['FEATURE_FLAGS_NEW_SUPPLIER_FLOW'], "%Y-%m-%d")
        <= datetime.strptime(brief['publishedAt'][0:10], "%Y-%m-%d")
    )

    counter = Counter()

    for response in brief_responses:
        counter[all(response['essentialRequirements'])] += 1

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    return render_template(
        "buyers/brief_responses.html",
        response_counts={"failed": counter[False], "eligible": counter[True]},
        brief_responses_require_evidence=brief_responses_require_evidence,
        brief=brief,
        breadcrumbs=breadcrumbs
    ), 200


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/award', methods=['GET', 'POST'])
def award_or_cancel_brief(framework_slug, lot_slug, brief_id):
    form = None
    errors = {}
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True,
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(
        brief, framework_slug, lot_slug, current_user.id,
        allowed_statuses=["awarded", "cancelled", "unsuccessful", "closed"]
    ):
        abort(404)

    breadcrumbs = get_briefs_breadcrumbs([{
        "label": brief['title'],
        "link": url_for(
            ".view_brief_overview",
            framework_slug=brief['frameworkSlug'],
            lot_slug=brief['lotSlug'],
            brief_id=brief['id']
        )
    }])

    if brief['status'] in ["awarded", "cancelled", "unsuccessful"]:
        already_awarded = True
    else:
        already_awarded = False

        if request.method == "POST":
            form = AwardOrCancelBriefForm(brief, request.form)
            if not form.validate_on_submit():
                errors = {
                    key: {'question': form[key].label.text, 'input_name': key, 'message': form[key].errors[0]}
                    for key, value in form.errors.items()
                }
            else:
                answer = form.data.get('award_or_cancel_decision')
                if answer == 'back':
                    flash(BRIEF_UPDATED_MESSAGE.format(brief=brief))
                    return redirect(url_for('.buyer_dos_requirements'))
                elif answer == 'yes':
                    return redirect(
                        url_for('.award_brief', framework_slug=framework_slug, lot_slug=lot_slug, brief_id=brief_id)
                    )
                elif answer == 'no':
                    return redirect(url_for(
                        '.cancel_award_brief', framework_slug=framework_slug, lot_slug=lot_slug, brief_id=brief_id)
                    )
                else:
                    # We should never get here as the form validates the answers against the available choices.
                    abort(500, "Unexpected answer to award or cancel brief")

    return render_template(
        "buyers/award_or_cancel_brief.html",
        brief=brief,
        form=form or AwardOrCancelBriefForm(brief),
        errors=errors,
        breadcrumbs=breadcrumbs,
        already_awarded=already_awarded,
    ), 200 if not errors else 400


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/award-contract', methods=['GET', 'POST'])
def award_brief(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True,
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id, allowed_statuses=['closed']):
        abort(404)

    brief_responses = data_api_client.find_brief_responses(
        brief['id'], status="submitted,pending-awarded"
    )['briefResponses']
    if not brief_responses:
        return redirect(
            url_for(
                ".view_brief_responses",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']
            )
        )

    if request.method == "POST":
        form = AwardedBriefResponseForm(brief_responses, request.form)
        if not form.validate_on_submit():
            form_errors = [{'question': form[key].label.text, 'input_name': key} for key in form.errors]
            return render_template(
                "buyers/award.html",
                brief=brief,
                form=form,
                form_errors=form_errors,
                breadcrumbs=breadcrumbs,
            ), 400

        if form.data:
            try:
                data_api_client.update_brief_award_brief_response(
                    brief_id,
                    form.data['brief_response'],
                    current_user.email_address
                )
            except HTTPError as e:
                abort(500, "Unexpected API error when awarding brief response")

            return redirect(
                url_for(
                    ".award_brief_details",
                    framework_slug=brief['frameworkSlug'],
                    lot_slug=brief['lotSlug'],
                    brief_id=brief['id'],
                    brief_response_id=form.data['brief_response']
                )
            )

    form = AwardedBriefResponseForm(brief_responses)
    pending_brief_responses = list(filter(lambda x: x.get('awardDetails', {}).get('pending'), brief_responses))
    form['brief_response'].data = pending_brief_responses[0]["id"] if pending_brief_responses else None

    return render_template(
        "buyers/award.html",
        brief=brief,
        form=form,
        breadcrumbs=breadcrumbs,
    ), 200


@main.route(
    '/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/cancel',
    methods=['GET', 'POST'],
)
@main.route(
    '/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/cancel-award',
    methods=['GET', 'POST'],
    endpoint="cancel_award_brief"
)
def cancel_brief(framework_slug, lot_slug, brief_id):
    form = None
    errors = {}
    award_flow = request.endpoint.strip(request.blueprint + '.') == 'cancel_award_brief'

    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True,
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]
    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id, allowed_statuses=['closed']):
        abort(404)

    if award_flow:
        label_text = "Why didn't you award a contract for {}?"
        previous_page_url = url_for(
            '.award_or_cancel_brief',
            framework_slug=brief['frameworkSlug'],
            lot_slug=brief['lotSlug'],
            brief_id=brief['id']
        )
    else:
        # Use default label text
        label_text = 'Why do you need to cancel {}?'
        previous_page_url = url_for(
            '.view_brief_overview',
            framework_slug=brief['frameworkSlug'],
            lot_slug=brief['lotSlug'],
            brief_id=brief['id']
        )
    if request.method == "POST":
        form = CancelBriefForm(brief, label_text, request.form)
        if not form.validate_on_submit():
            errors = {
                key: {'question': form[key].label.text, 'input_name': key, 'message': form[key].errors[0]}
                for key, value in form.errors.items()
            }
        else:
            new_status = form.data.get('cancel_reason')
            try:
                if new_status == 'cancel':
                    data_api_client.cancel_brief(
                        brief_id,
                        user=current_user.email_address
                    )
                elif new_status == 'unsuccessful':
                    data_api_client.update_brief_as_unsuccessful(
                        brief_id,
                        user=current_user.email_address
                    )
                else:
                    abort(400, "Unrecognized status '{}'".format(new_status))
                flash(BRIEF_UPDATED_MESSAGE.format(brief=brief))
                return redirect(
                    url_for('.view_brief_overview', framework_slug=framework_slug, lot_slug=lot_slug, brief_id=brief_id)
                )
            except HTTPError as e:
                abort(500, "Unexpected API error when cancelling brief")

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    return render_template(
        "buyers/cancel_brief.html",
        brief=brief,
        form=form or CancelBriefForm(brief, label_text),
        errors=errors,
        breadcrumbs=breadcrumbs,
        previous_page_url=previous_page_url
    ), 200 if not errors else 400


@main.route(
    '/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/award/<brief_response_id>/contract-details',
    methods=['GET', 'POST']
)
def award_brief_details(framework_slug, lot_slug, brief_id, brief_response_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True,
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]
    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id):
        abort(404)
    brief_response = data_api_client.get_brief_response(brief_response_id)["briefResponses"]
    if not brief_response.get('status') == 'pending-awarded' or not brief_response.get('briefId') == brief.get('id'):
        abort(404)
    # get questions
    content = content_loader.get_manifest(brief['frameworkSlug'], 'award_brief')
    section_id = content.get_next_editable_section_id()
    section = content.get_section(section_id)

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    if request.method == "POST":
        award_data = section.get_data(request.form)
        try:
            data_api_client.update_brief_award_details(
                brief_id,
                brief_response_id,
                award_data,
                updated_by=current_user.email_address
            )
        except HTTPError as e:
            award_data = section.unformat_data(award_data)
            errors = section.get_error_messages(e.message)

            return render_template(
                "buyers/award_details.html",
                brief=brief,
                data=award_data,
                errors=errors,
                pending_brief_response=brief_response,
                section=section,
                breadcrumbs=breadcrumbs,
            ), 400

        flash(BRIEF_UPDATED_MESSAGE.format(brief=brief))

        if flask_featureflags.is_active('DIRECT_AWARD_PROJECTS'):
            return redirect(url_for(".buyer_dos_requirements"))

        return redirect(url_for(".buyer_dashboard"))

    return render_template(
        "buyers/award_details.html",
        brief=brief,
        data={},
        pending_brief_response=brief_response,
        section=section,
        breadcrumbs=breadcrumbs,
    ), 200


class DownloadBriefResponsesView(DownloadFileView):
    def get_responses(self, brief):
        return get_sorted_responses_for_brief(brief, self.data_api_client)

    def _init_hook(self, **kwargs):
        self.data_api_client = data_api_client
        self.content_loader = content_loader

    def determine_filetype(self, file_context=None, **kwargs):
        responses = file_context['responses']

        if responses and 'essentialRequirementsMet' in responses[0]:
            return DownloadFileView.FILETYPES.ODS

        return DownloadFileView.FILETYPES.CSV

    def get_file_context(self, **kwargs):
        get_framework_and_lot(
            kwargs['framework_slug'],
            kwargs['lot_slug'],
            self.data_api_client,
            allowed_statuses=['live', 'expired'],
            must_allow_brief=True,
        )

        brief = self.data_api_client.get_brief(kwargs['brief_id'])["briefs"]

        if not is_brief_correct(brief, kwargs['framework_slug'],
                                kwargs['lot_slug'], current_user.id):
            abort(404)

        if brief['status'] not in CLOSED_PUBLISHED_BRIEF_STATUSES:
            abort(404)

        file_context = {
            'brief': brief,
            'responses': self.get_responses(brief),
            'filename': 'supplier-responses-{0}'.format(inflection.parameterize(str(brief['title']))),
        }

        return file_context

    def get_questions(self, framework_slug, lot_slug, manifest):
        section = 'view-response-to-requirements'
        result = self.content_loader.get_manifest(framework_slug, manifest)\
                                    .filter({'lot': lot_slug}, dynamic=False)\
                                    .get_section(section)

        return result.questions if result else []

    def generate_csv_rows(self, file_context):
        column_headings = []
        question_key_sequence = []
        boolean_list_questions = []
        csv_rows = []
        brief, responses = file_context['brief'], file_context['responses']

        questions = self.get_questions(brief['frameworkSlug'],
                                       brief['lotSlug'],
                                       'legacy_output_brief_response')

        # Build header row from manifest and add it to the list of rows
        for question in questions:
            question_key_sequence.append(question.id)
            if question['type'] == 'boolean_list' and brief.get(question.id):
                column_headings.extend(brief[question.id])
                boolean_list_questions.append(question.id)
            else:
                column_headings.append(question.name)
        csv_rows.append(column_headings)

        # Add a row for each eligible response received
        for brief_response in responses:
            if all(brief_response['essentialRequirements']):
                row = []
                for key in question_key_sequence:
                    if key in boolean_list_questions:
                        row.extend(brief_response.get(key))
                    else:
                        row.append(brief_response.get(key))
                csv_rows.append(row)

        return csv_rows

    def populate_styled_ods_with_data(self, spreadsheet, file_context):
        sheet = spreadsheet.sheet("Supplier evidence")

        brief, responses = file_context['brief'], file_context['responses']
        questions = self.get_questions(brief['frameworkSlug'],
                                       brief['lotSlug'],
                                       'output_brief_response')

        # two intro columns for boolean and dynamic lists
        sheet.create_column(stylename="col-wide", defaultcellstylename="cell-default")
        sheet.create_column(stylename="col-wide", defaultcellstylename="cell-default")

        # HEADER
        row = sheet.create_row("header", stylename="row-tall")
        row.write_cell(brief['title'], stylename="cell-header", numbercolumnsspanned=str(len(responses) + 2))

        # QUESTIONS
        for question in questions:
            if question._data['type'] in ('boolean_list', 'dynamic_list'):
                length = len(brief[question.id])

                for i, requirement in enumerate(brief[question.id]):
                    row = sheet.create_row("{0}[{1}]".format(question.id, i))
                    if i == 0:
                        row.write_cell(question.name, stylename="cell-header", numberrowsspanned=str(length))
                    else:
                        row.write_covered_cell()
                    row.write_cell(requirement, stylename="cell-default")
            else:
                row = sheet.create_row(question.id, stylename="row-tall-optimal")
                row.write_cell(question.name, stylename="cell-header", numbercolumnsspanned="2")
                row.write_covered_cell()

        # RESPONSES
        for response in responses:
            sheet.create_column(stylename="col-extra-wide", defaultcellstylename="cell-default")

            for question in questions:
                if question._data['type'] == 'dynamic_list':
                    if not brief.get(question.id):
                        continue

                    for i, item in enumerate(response[question.id]):
                        row = sheet.get_row("{0}[{1}]".format(question.id, i))
                        # TODO this is stupid, fix it (key should not be hard coded)
                        row.write_cell(item.get('evidence') or '', stylename="cell-default")

                elif question.type == 'boolean_list' and brief.get(question.id):
                    if not brief.get(question.id):
                        continue

                    for i, item in enumerate(response[question.id]):
                        row = sheet.get_row("{0}[{1}]".format(question.id, i))
                        row.write_cell(str(bool(item)).lower(), stylename="cell-default")

                else:
                    sheet.get_row(question.id).write_cell(response.get(question.id, ''), stylename="cell-default")

        return spreadsheet


main.add_url_rule('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/responses/download',
                  view_func=DownloadBriefResponsesView.as_view(str('download_brief_responses')),
                  methods=['GET'])


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
        if sections.get_section('set-how-long-your-requirements-will-be-open-for') and \
                sections.get_section('set-how-long-your-requirements-will-be-open-for').questions[0].answer_required:
                unanswered_required -= 1

        email_address = brief_users['emailAddress']
        dates = get_publishing_dates(brief)

        breadcrumbs = get_briefs_breadcrumbs([
            {
                "link": url_for(
                    ".view_brief_overview",
                    framework_slug=brief['frameworkSlug'],
                    lot_slug=brief['lotSlug'],
                    brief_id=brief['id']),
                "label": brief['title']
            }
        ])

        return render_template(
            "buyers/brief_publish_confirmation.html",
            email_address=email_address,
            question_and_answers=question_and_answers,
            unanswered_required=unanswered_required,
            sections=sections,
            brief=brief,
            dates=dates,
            breadcrumbs=breadcrumbs
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
    flash(BRIEF_DELETED_MESSAGE.format(brief=brief))

    if flask_featureflags.is_active('DIRECT_AWARD_PROJECTS'):
        return redirect(url_for(".buyer_dos_requirements"))

    return redirect(url_for('.buyer_dashboard'))


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
    flash(BRIEF_WITHDRAWN_MESSAGE.format(brief=brief))

    if flask_featureflags.is_active('DIRECT_AWARD_PROJECTS'):
        return redirect(url_for(".buyer_dos_requirements"))

    return redirect(url_for('.buyer_dashboard'))


@main.route(
    "/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/supplier-questions",
    methods=["GET"])
def supplier_questions(framework_slug, lot_slug, brief_id):
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

    brief['clarificationQuestions'] = [
        dict(question, number=index + 1)
        for index, question in enumerate(brief['clarificationQuestions'])
    ]

    breadcrumbs = get_briefs_breadcrumbs()

    return render_template(
        "buyers/supplier_questions.html",
        brief=brief,
        breadcrumbs=breadcrumbs,
    )


@main.route(
    "/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/supplier-questions/answer-question",
    methods=["GET", "POST"])
def add_supplier_question(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug, data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id, allowed_statuses=['live']):
        abort(404)

    content = content_loader.get_manifest(brief['frameworkSlug'], "clarification_question").filter({})
    section = content.get_section(content.get_next_editable_section_id())
    update_data = section.get_data(request.form)

    errors = {}
    status_code = 200

    if request.method == "POST":
        try:
            data_api_client.add_brief_clarification_question(brief_id,
                                                             update_data['question'],
                                                             update_data['answer'],
                                                             current_user.email_address)

            return redirect(
                url_for('.supplier_questions', framework_slug=brief['frameworkSlug'], lot_slug=brief['lotSlug'],
                        brief_id=brief['id']))
        except HTTPError as e:
            if e.status_code != 400:
                raise
            brief.update(update_data)
            errors = section.get_error_messages(e.message)
            status_code = 400

    breadcrumbs = get_briefs_breadcrumbs([
        {
            "link": url_for(
                ".view_brief_overview",
                framework_slug=brief['frameworkSlug'],
                lot_slug=brief['lotSlug'],
                brief_id=brief['id']),
            "label": brief['title']
        }
    ])

    return render_template(
        "buyers/edit_brief_question.html",
        brief=brief,
        section=section,
        question=section.questions[0],
        button_label="Publish question and answer",
        errors=errors,
        breadcrumbs=breadcrumbs
    ), status_code
