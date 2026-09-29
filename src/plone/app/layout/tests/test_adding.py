from Acquisition import aq_get
from plone.app.content.testing import PLONE_APP_CONTENT_INTEGRATION_TESTING

import unittest


class AddingTests(unittest.TestCase):
    layer = PLONE_APP_CONTENT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_adding_acquisition(self):
        adding = self.portal.unrestrictedTraverse("+")
        # Check explicit Acquisition
        template = aq_get(adding, "portal_skins")
        self.assertTrue(template)
        # Check implicit Acquisition, unfortunately the CMF skins machinery
        # depends on this
        template = getattr(adding, "portal_skins")
        self.assertTrue(template)
        # Check traversal
        self.assertTrue(self.portal.unrestrictedTraverse("+/main_template"))
