from plone.app.layout.testing import PLONE_APP_LAYOUT_FUNCTIONAL_TESTING
from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from plone.app.layout.testing import TEST_USER_ID

import unittest


class ViewletsTestCase(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.app = self.layer["app"]
        self.folder = self.portal["Members"][TEST_USER_ID]


class ViewletsFunctionalTestCase(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.app = self.layer["app"]
        self.folder = self.portal["Members"][TEST_USER_ID]
