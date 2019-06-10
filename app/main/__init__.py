from functools import partial
from flask import Blueprint
from dmcontent.content_loader import ContentLoader
from dmutils.access_control import require_login


main = Blueprint('buyers', __name__)
dos = Blueprint('dos', __name__)

content_loader = ContentLoader('app/content')
content_loader.load_manifest('digital-outcomes-and-specialists', 'briefs', 'edit_brief')
content_loader.load_manifest('digital-outcomes-and-specialists', 'brief-responses', 'output_brief_response')
content_loader.load_manifest('digital-outcomes-and-specialists', 'brief-responses', 'legacy_output_brief_response')
content_loader.load_manifest('digital-outcomes-and-specialists', 'clarification_question', 'clarification_question')
content_loader.load_manifest('digital-outcomes-and-specialists', 'briefs', 'award_brief')

content_loader.load_manifest('digital-outcomes-and-specialists-2', 'briefs', 'edit_brief')
content_loader.load_manifest('digital-outcomes-and-specialists-2', 'brief-responses', 'output_brief_response')
content_loader.load_manifest('digital-outcomes-and-specialists-2', 'clarification_question', 'clarification_question')
content_loader.load_manifest('digital-outcomes-and-specialists-2', 'briefs', 'award_brief')

content_loader.load_manifest('digital-outcomes-and-specialists-3', 'briefs', 'edit_brief')
content_loader.load_manifest('digital-outcomes-and-specialists-3', 'brief-responses', 'output_brief_response')
content_loader.load_manifest('digital-outcomes-and-specialists-3', 'clarification_question', 'clarification_question')
content_loader.load_manifest('digital-outcomes-and-specialists-3', 'briefs', 'award_brief')

content_loader.load_manifest('digital-outcomes-and-specialists-4', 'briefs', 'edit_brief')
content_loader.load_manifest('digital-outcomes-and-specialists-4', 'brief-responses', 'output_brief_response')
content_loader.load_manifest('digital-outcomes-and-specialists-4', 'clarification_question', 'clarification_question')
content_loader.load_manifest('digital-outcomes-and-specialists-4', 'briefs', 'award_brief')


main.before_request(partial(require_login, role='buyer'))


@main.after_request
def add_cache_control(response):
    response.cache_control.no_cache = True
    return response


from ..main import errors
from .views import buyers as buyers_views
from .views import supplier_questions as supplier_questions_views
from .views import outcome as outcome_views
from .views import download_responses as download_responses_views
from .views import digital_outcomes_and_specialists
