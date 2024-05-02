from plone.app.layout.testing import INTEGRATION_TESTING
from Products.CMFCore.utils import getToolByName

import unittest


class TestToolsView(unittest.TestCase):
    """Tests the global tools view."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.folder = self.portal["Members"]
        self.view = self.folder.restrictedTraverse("@@plone_tools")

    def test_actions(self):
        self.assertEqual(
            self.view.actions(), getToolByName(self.folder, "portal_actions")
        )

    def test_catalog(self):
        self.assertEqual(
            self.view.catalog(), getToolByName(self.folder, "portal_catalog")
        )

    def test_membership(self):
        self.assertEqual(
            self.view.membership(), getToolByName(self.folder, "portal_membership")
        )

    def test_properties(self):
        self.assertEqual(
            self.view.properties(), getToolByName(self.folder, "portal_properties")
        )

    def test_types(self):
        self.assertEqual(self.view.types(), getToolByName(self.folder, "portal_types"))

    def test_url(self):
        self.assertEqual(self.view.url(), getToolByName(self.folder, "portal_url"))

    def test_workflow(self):
        self.assertEqual(
            self.view.workflow(), getToolByName(self.folder, "portal_workflow")
        )
