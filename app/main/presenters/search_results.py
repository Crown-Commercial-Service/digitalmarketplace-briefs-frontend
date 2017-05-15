from flask import Markup


class SearchResults(object):
    """Provides access to the search results information"""

    def __init__(self, response, lots_by_slug):
        self.search_results = response['services']
        self._lots = lots_by_slug
        self._annotate()
        self.total = response['meta']['total']
        if 'page' in response['meta']['query']:
            self.page = response['meta']['query']['page']

    def _annotate(self):
        for service in self.search_results:
            self._replace_lot(service)
            self._add_highlighting(service)

    def _replace_lot(self, service):
        # replace lot slug with reference to dict containing all the relevant lot data
        service['lot'] = self._lots.get(service['lot'])

    def _add_highlighting(self, service):
        if 'highlight' in service:
            if 'serviceSummary' in service['highlight']:
                service['serviceSummary'] = Markup(
                    ''.join(service['highlight']['serviceSummary'])
                )