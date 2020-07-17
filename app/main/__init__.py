from copy import deepcopy
from functools import partial

from flask import Blueprint
from werkzeug.local import Local, LocalProxy

from dmcontent.content_loader import ContentLoader
from dmutils.access_control import require_login
from dmutils.timing import logged_duration


main = Blueprint('buyers', __name__)
dos = Blueprint('dos', __name__)

# we use our own Local for objects we explicitly want to be able to retain between requests but shouldn't
# share a common object between concurrent threads/contexts
_local = Local()


def _make_content_loader_factory():
    master_cl = ContentLoader('app/content')
    master_cl.load_manifest('digital-outcomes-and-specialists', 'briefs', 'edit_brief')
    master_cl.load_manifest('digital-outcomes-and-specialists', 'brief-responses', 'output_brief_response')
    master_cl.load_manifest('digital-outcomes-and-specialists', 'brief-responses', 'legacy_output_brief_response')
    master_cl.load_manifest('digital-outcomes-and-specialists', 'clarification_question', 'clarification_question')
    master_cl.load_manifest('digital-outcomes-and-specialists', 'briefs', 'award_brief')

    master_cl.load_manifest('digital-outcomes-and-specialists-2', 'briefs', 'edit_brief')
    master_cl.load_manifest('digital-outcomes-and-specialists-2', 'brief-responses', 'output_brief_response')
    master_cl.load_manifest('digital-outcomes-and-specialists-2', 'clarification_question', 'clarification_question')
    master_cl.load_manifest('digital-outcomes-and-specialists-2', 'briefs', 'award_brief')

    master_cl.load_manifest('digital-outcomes-and-specialists-3', 'briefs', 'edit_brief')
    master_cl.load_manifest('digital-outcomes-and-specialists-3', 'brief-responses', 'output_brief_response')
    master_cl.load_manifest('digital-outcomes-and-specialists-3', 'clarification_question', 'clarification_question')
    master_cl.load_manifest('digital-outcomes-and-specialists-3', 'briefs', 'award_brief')

    master_cl.load_manifest('digital-outcomes-and-specialists-4', 'briefs', 'edit_brief')
    master_cl.load_manifest('digital-outcomes-and-specialists-4', 'briefs', 'display_brief')
    master_cl.load_manifest('digital-outcomes-and-specialists-4', 'brief-responses', 'output_brief_response')
    master_cl.load_manifest('digital-outcomes-and-specialists-4', 'clarification_question', 'clarification_question')
    master_cl.load_manifest('digital-outcomes-and-specialists-4', 'briefs', 'award_brief')

    # seal master_cl in a closure by returning a function which will only ever return an independent copy of it
    return lambda: deepcopy(master_cl)


_content_loader_factory = _make_content_loader_factory()


@logged_duration(message="Spent {duration_real}s in get_content_loader")
def get_content_loader():
    if not hasattr(_local, "content_loader"):
        _local.content_loader = _content_loader_factory()
    return _local.content_loader


content_loader = LocalProxy(get_content_loader)


main.before_request(partial(require_login, role='buyer'))


@main.after_request
def add_cache_control(response):
    response.cache_control.no_cache = True
    return response


from ..main import errors
from .views import create_a_requirement as create_a_requirement_views
from .views import buyers as buyers_views
from .views import supplier_questions as supplier_questions_views
from .views import outcome as outcome_views
from .views import download_responses as download_responses_views
from .views import digital_outcomes_and_specialists
