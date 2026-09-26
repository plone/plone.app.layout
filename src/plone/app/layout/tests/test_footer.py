from DateTime import DateTime
from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from zope.component import getMultiAdapter

import unittest


class TestFooterView(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_using_correct_template(self):
        """Ensure that the footer view uses the template from plone.app.layout."""
        view = getMultiAdapter((self.portal, self.request), name="footer")
        self.assertIn("plone/app/layout/views/templates/footer.pt", view.index.filename)

    def test_render(self):
        view = getMultiAdapter((self.portal, self.request), name="footer")
        result = view()
        self.assertIn('id="portal-footer-signature"', result)
        self.assertIn(str(DateTime().year()), result)
