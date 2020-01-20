# coding: utf-8
from __future__ import unicode_literals

from flask import abort, request, redirect, url_for
from flask_login import current_user

from app import data_api_client
from .. import main, content_loader
from ..helpers.buyers_helpers import get_framework_and_lot, is_brief_correct

from dmapiclient import HTTPError
from dmutils.flask import timed_render_template as render_template


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

    return render_template(
        "buyers/supplier_questions.html",
        brief=brief
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

    return render_template(
        "buyers/edit_brief_question.html",
        brief=brief,
        section=section,
        question=section.questions[0],
        button_label="Publish question and answer",
        errors=errors
    ), status_code
