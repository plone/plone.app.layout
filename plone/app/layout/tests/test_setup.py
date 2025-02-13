from plone.app.layout.testing import INTEGRATION_TESTING
from plone.base.utils import get_installer

import unittest


class TestSetup(unittest.TestCase):
    """Test plone.app.layout setup."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_browserlayer(self):
        from plone.app.layout.interfaces import IPloneAppLayoutLayer
        from plone.browserlayer import utils

        self.assertIn(IPloneAppLayoutLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        self.installer = get_installer(self.portal, self.request)
        self.installer.uninstall_product("plone.app.layout")

    def test_browserlayer_removed(self):
        from plone.app.layout.interfaces import IPloneAppLayoutLayer
        from plone.browserlayer import utils

        self.assertNotIn(IPloneAppLayoutLayer, utils.registered_layers())
