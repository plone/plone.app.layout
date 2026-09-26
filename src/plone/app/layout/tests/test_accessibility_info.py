from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from zope.component import getMultiAdapter

import unittest


class TestAccessibilityInfoView(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_using_correct_template(self):
        """Ensure that the accessibility-info view uses the template from plone.app.layout."""
        view = getMultiAdapter((self.portal, self.request), name="accessibility-info")
        self.assertIn(
            "plone/app/layout/views/templates/accessibility-info.pt",
            view.index.filename,
        )

    def test_render(self):
        view = getMultiAdapter((self.portal, self.request), name="accessibility-info")
        self.assertIn("Accessibility Statement", view())
