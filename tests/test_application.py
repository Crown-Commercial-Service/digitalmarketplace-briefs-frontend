from .helpers import BaseApplicationTest


class TestApplication(BaseApplicationTest):
    def test_404(self):
        response = self.client.get('/buyers/not-found')
        assert 404 == response.status_code

    def test_trailing_slashes(self):
        response = self.client.get('/buyers/')
        assert 301 == response.status_code
        assert "http://localhost/buyers" == response.location

    def test_header_xframeoptions_set_to_deny(self):
        res = self.client.get('/buyers')
        assert 302 == res.status_code
        assert 'DENY', res.headers['X-Frame-Options']
