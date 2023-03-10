from plone.base.navigationroot import get_navigation_root_object
from plone.app.layout.testing import INTEGRATION_TESTING

import unittest


class NavigationRootTestCase(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def test_getNavigationRootObject_no_context(self):
        """
        If you don't know the context then you also don't know what the
        navigation root is.
        """
        self.portal = self.layer["portal"]
        self.assertEqual(None, get_navigation_root_object(None, self.portal))
