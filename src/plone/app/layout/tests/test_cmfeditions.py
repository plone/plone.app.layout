"""Test the versions_history_form view, moved here from Products.CMFEditions."""

from plone.app.layout.tests.cmfeditions_testing import CMFEDITIONS_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.textfield.value import RichTextValue
from Products.Five.browser import BrowserView
from zope.component import provideAdapter
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserView

import unittest


_TEXT_INITIAL = "Initial text."
_TEXT_NEW = "New text."


class TestVersionsHistoryForm(unittest.TestCase):
    layer = CMFEDITIONS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_repository = self.portal.portal_repository
        self.portal.invokeFactory(
            "Document",
            "doc",
            title="Document 1",
            text=RichTextValue(_TEXT_INITIAL, "text/plain", "text/plain"),
        )
        self.doc = self.portal.doc
        self.portal_repository.applyVersionControl(self.doc, comment="save version 0")
        self.request = self.portal.REQUEST

    def test_versions_history_form(self):
        self.doc.text = RichTextValue(_TEXT_NEW, "text/plain", "text/plain")
        self.portal_repository.save(self.doc, comment="save version 1")

        html = self._render_versions_history_form(item=self.doc, version_id="0")
        self.assertTrue(_TEXT_INITIAL in html)
        self.assertFalse(_TEXT_NEW in html)

        html = self._render_versions_history_form(item=self.doc, version_id="1")
        self.assertFalse(_TEXT_INITIAL in html)
        self.assertTrue(_TEXT_NEW in html)

    def test_versions_history_form_custom_version_view(self):
        """Assert that if we define an @@version-view then it will be used to
        display the versions.
        """
        dummy_str = "Blah"

        class DummyVersionView(BrowserView):
            def __call__(self):
                return dummy_str

        provideAdapter(
            factory=DummyVersionView,
            adapts=(Interface, Interface),
            provides=IBrowserView,
            name="version-view",
        )

        html = self._render_versions_history_form(item=self.doc, version_id="0")
        self.assertTrue(dummy_str in html)
        self.assertFalse(_TEXT_INITIAL in html)

    def _render_versions_history_form(self, item, version_id):
        self.request["version_id"] = version_id
        return item.unrestrictedTraverse("versions_history_form")()
