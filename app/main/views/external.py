from .. import external


@external.route('/<framework_framework>/opportunities/<brief_id>')
def get_brief_by_id(framework_framework, brief_id):
    raise NotImplementedError()
