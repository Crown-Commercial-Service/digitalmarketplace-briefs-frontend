from flask import abort, request, redirect, url_for
from flask_login import current_user

from app import data_api_client
from ... import main, content_loader
from ...helpers.buyers_helpers import (
    get_framework_and_lot,
    is_brief_correct,
)

from dmapiclient import HTTPError
from dmutils.flask import timed_render_template as render_template
from dmutils.forms.errors import govuk_errors


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
        errors = govuk_errors(section.get_error_messages(e.message))

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
