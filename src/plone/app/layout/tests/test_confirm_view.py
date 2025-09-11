from plone.app.layout.testing import INTEGRATION_TESTING
from zope.component import getMultiAdapter

import unittest


class TestAttackVector(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def test_using_correct_template(self):
        """Ensure that confirm-action view uses the confirm.pt template from plone.app.layout."""
        portal = self.layer["portal"]
        request = self.layer["request"]
        view = getMultiAdapter((portal, request), name="confirm-action")

        self.assertIn("plone/app/layout/views/confirm.pt", view.index.filename)
