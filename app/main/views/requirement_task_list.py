from flask import abort, request, url_for
from flask_login import current_user

from dmutils.flask import timed_render_template as render_template

from app import data_api_client
from .. import main, content_loader
from ..helpers.buyers_helpers import (
    count_unanswered_questions,
    get_framework_and_lot,
    is_brief_correct,
    section_has_at_least_one_required_question,
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
        call_off_contract_url=call_off_contract_url,
        framework_agreement_url=framework_agreement_url,
        awarded_brief_response_supplier_name=awarded_brief_response_supplier_name,
        publish_requirements_section_links=publish_requirements_section_links
    ), 200
