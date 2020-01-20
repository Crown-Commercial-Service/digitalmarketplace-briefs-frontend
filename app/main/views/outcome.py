# coding: utf-8
from __future__ import unicode_literals


from flask import abort, request, redirect, url_for, flash
from flask_login import current_user

from app import data_api_client
from .. import main, content_loader
from ..helpers.buyers_helpers import get_framework_and_lot, is_brief_correct

from ..forms.awards import AwardedBriefResponseForm
from ..forms.cancel import CancelBriefForm
from ..forms.award_or_cancel import AwardOrCancelBriefForm

from dmapiclient import HTTPError
from dmutils.flask import timed_render_template as render_template
from dmutils.forms.helpers import get_errors_from_wtform

BRIEF_UPDATED_MESSAGE = "You’ve updated ‘{brief[title]}’"


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/award', methods=['GET', 'POST'])
def award_or_cancel_brief(framework_slug, lot_slug, brief_id):
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

    form = AwardOrCancelBriefForm(brief)
    already_awarded = brief['status'] in ["awarded", "cancelled", "unsuccessful"]

    if already_awarded is False and form.validate_on_submit():
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

    errors = get_errors_from_wtform(form)

    return render_template(
        "buyers/award_or_cancel_brief.html",
        brief=brief,
        form=form,
        errors=errors,
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

    form = AwardedBriefResponseForm(brief_responses)

    if form.validate_on_submit():
        try:
            data_api_client.update_brief_award_brief_response(
                brief_id,
                form.data['brief_response'],
                current_user.email_address
            )
        except HTTPError:
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

    pending_brief_responses = list(filter(lambda x: x.get('awardDetails', {}).get('pending'), brief_responses))
    form['brief_response'].data = pending_brief_responses[0]["id"] if pending_brief_responses else None
    errors = get_errors_from_wtform(form)

    return render_template(
        "buyers/award.html",
        brief=brief,
        form=form,
        errors=errors
    ), 200 if not errors else 400


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
        label_text = "Why didn’t you award a contract for {}?"
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

    form = CancelBriefForm(brief, label_text)

    if form.validate_on_submit():
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
        except HTTPError:
            abort(500, "Unexpected API error when cancelling brief")

    errors = get_errors_from_wtform(form)

    return render_template(
        "buyers/cancel_brief.html",
        brief=brief,
        form=form,
        errors=errors,
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
                section=section
            ), 400

        flash(BRIEF_UPDATED_MESSAGE.format(brief=brief))

        return redirect(url_for(".buyer_dos_requirements"))

    return render_template(
        "buyers/award_details.html",
        brief=brief,
        data={},
        pending_brief_response=brief_response,
        section=section
    ), 200
