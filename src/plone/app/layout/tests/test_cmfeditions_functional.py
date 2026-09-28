"""Functional test for the versions_history_form Classic UI page.

Moved here from plone.app.versioningbehavior's test_functional.py: this
exercises the Classic UI HTML rendering that lives in plone.app.layout, not
the versioning behavior/API itself (which plone.app.versioningbehavior still
tests directly, without needing plone.app.layout).
"""

from plone.app.layout.testing import PLONE_APP_LAYOUT_FUNCTIONAL_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.testing.zope import Browser

import transaction
import unittest


class TestVersionsHistoryFormFunctional(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory("Document", "doc", title="Old Title")
        self.doc = self.portal["doc"]
        transaction.commit()

        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )

    def test_versions_history_form_renders_revision_markup(self):
        self.browser.open(self.doc.absolute_url() + "/edit")
        self.browser.getControl(label="Title").value = "New Title"
        self.browser.getControl(name="form.buttons.save").click()

        self.browser.open(
            f"{self.doc.absolute_url()}/versions_history_form?version_id=0"
        )
        self.assertIn("Current revision", self.browser.contents)
        self.assertIn("/doc/versions_history_form?version_id=0", self.browser.contents)
        self.assertIn("Revert to this revision", self.browser.contents)
        self.assertIn("/doc/@@history?one", self.browser.contents)
        self.assertIn("Preview of Revision 0", self.browser.contents)
        self.assertIn(
            '<h1 class="documentFirstHeading">Old Title</h1>', self.browser.contents
        )
