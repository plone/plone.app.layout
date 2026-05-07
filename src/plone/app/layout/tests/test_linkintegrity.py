"""Functional tests for link integrity HTML rendering.

These tests verify that the delete confirmation page correctly renders
link integrity warnings (HTML). The underlying API logic (get_breaches etc.)
is tested in plone.app.linkintegrity.
"""

from plone.app.layout import testing
from plone.app.linkintegrity.testing import create
from plone.app.linkintegrity.testing import GIF
from plone.app.linkintegrity.utils import getIncomingLinks
from plone.app.linkintegrity.utils import getOutgoingLinks
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.app.textfield import RichTextValue
from plone.base.interfaces import IEditingSchema
from plone.registry.interfaces import IRegistry
from plone.testing.zope import Browser
from zc.relation.interfaces import ICatalog
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.lifecycleevent import modified

import re
import transaction
import unittest


def set_text(obj, text):
    obj.text = RichTextValue(text)
    modified(obj)


class LinkIntegrityFunctionalTestCase(unittest.TestCase):
    """Functional tests for link integrity HTML rendering in delete confirmation."""

    layer = testing.FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        # Create sample content
        for i in range(1, 4):
            create(self.portal, "Document", id=f"doc{i}", title=f"Test Page {i}")
        create(self.portal, "File", id="file1", title="File 1", file=GIF)
        create(self.portal, "Folder", id="folder1", title="Folder 1")
        create(self.portal["folder1"], "Document", id="doc4", title="Test Page 4")

        # Get a testbrowser
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader("Referer", self.portal.absolute_url())
        self.browser.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )

        # Initial page load to compile bundles before rendering exception views
        transaction.commit()
        self.browser.open(self.portal.absolute_url())

    def _get_token(self, obj):
        return getMultiAdapter((obj, self.request), name="authenticator").token()

    def test_file_reference_linkintegrity_page_is_shown(self):
        doc1 = self.portal.doc1
        file2 = create(self.portal, "File", id="file2", file=GIF)

        set_text(doc1, '<a href="file2">A File</a>')
        token = self._get_token(file2)
        self.request["_authenticator"] = token
        transaction.commit()

        self.browser.handleErrors = True
        delete_url = "{}/delete_confirmation?_authenticator={}".format(
            file2.absolute_url(), token
        )
        self.browser.open(delete_url)
        self.assertIn("Potential link breakage", self.browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/doc1">Test Page 1</a>', self.browser.contents
        )
        self.assertIn("Would you like to delete it anyway?", self.browser.contents)

        self.browser.getControl(name="form.buttons.Delete").click()
        self.assertNotIn("file2", self.portal.objectIds())

    def test_renaming_referenced_item(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2

        set_text(doc1, '<a href="doc2">doc2</a>')
        self.assertEqual([i.from_object for i in getIncomingLinks(doc2)], [doc1])
        transaction.commit()

        self.browser.handleErrors = True
        self.browser.open(
            "{}/object_rename?_authenticator={}".format(
                doc1.absolute_url(), self._get_token(doc1)
            )
        )
        self.browser.getControl(name="form.widgets.new_id").value = "nuname"
        self.browser.getControl(name="form.buttons.Rename").click()
        self.assertIn("Renamed 'doc1' to 'nuname'.", self.browser.contents)
        transaction.commit()

        self.assertIn(doc1, [i.from_object for i in getIncomingLinks(doc2)])
        self.browser.open(doc2.absolute_url())
        self.browser.getLink("Delete").click()
        self.assertIn("Potential link breakage", self.browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/nuname">Test Page 1</a>',
            self.browser.contents,
        )
        self.browser.getControl(name="form.buttons.Delete").click()
        self.assertNotIn("doc2", self.portal.objectIds())

    def test_removal_in_subfolder(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2
        folder1 = self.portal.folder1

        set_text(doc1, '<a href="folder1/doc4">a document</a>')
        set_text(doc2, '<a href="folder1/doc4">a document</a>')
        transaction.commit()

        self.browser.handleErrors = True
        self.browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                folder1.absolute_url(), self._get_token(folder1)
            )
        )
        self.assertIn("Potential link breakage", self.browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/doc1">Test Page 1</a>', self.browser.contents
        )
        self.assertIn(
            '<a href="http://nohost/plone/doc2">Test Page 2</a>', self.browser.contents
        )
        self.browser.getControl(name="form.buttons.Delete").click()
        self.assertNotIn("folder1", self.portal.objectIds())

    def test_removal_with_cookie_auth(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2

        set_text(doc1, '<a href="doc2">doc2</a>')
        transaction.commit()

        browser = Browser(self.layer["app"])
        browser.handleErrors = True
        browser.addHeader("Referer", self.portal.absolute_url())
        browser.open(f"{self.portal.absolute_url()}/folder_contents")
        self.assertIn("login?came_from", browser.url)

        browser.getControl(name="__ac_name").value = TEST_USER_NAME
        browser.getControl(name="__ac_password").value = TEST_USER_PASSWORD
        browser.getControl("Log in").click()
        self.assertNotIn("authorization", [h.lower() for h in browser.headers.keys()])

        browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                doc2.absolute_url(), self._get_token(doc2)
            )
        )
        self.assertIn("Potential link breakage", browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/doc1">Test Page 1</a>', browser.contents
        )
        browser.getControl(name="form.buttons.Delete").click()
        self.assertNotIn("doc2", self.portal.objectIds())

    def test_linkintegrity_on_off_switch(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2

        set_text(doc1, '<a href="doc2">a document</a>')
        transaction.commit()

        self.browser.handleErrors = True
        self.browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                doc2.absolute_url(), self._get_token(doc2)
            )
        )
        self.assertIn("Potential link breakage", self.browser.contents)

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IEditingSchema, prefix="plone")
        settings.enable_link_integrity_checks = False
        transaction.commit()
        self.browser.reload()
        self.assertNotIn("Potential link breakage", self.browser.contents)

    def test_references_on_cloned_objects(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2

        set_text(doc1, '<a href="doc2">a document</a>')
        token = self._get_token(doc1)
        self.request["_authenticator"] = token
        doc1.restrictedTraverse("object_copy")()
        self.request["_authenticator"] = token
        self.portal.restrictedTraverse("object_paste")()
        self.assertIn("copy_of_doc1", self.portal)
        transaction.commit()

        self.browser.handleErrors = True
        self.browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                doc2.absolute_url(), self._get_token(doc2)
            )
        )
        self.assertIn("Potential link breakage", self.browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/doc1">Test Page 1</a>', self.browser.contents
        )
        self.assertIn(
            '<a href="http://nohost/plone/copy_of_doc1"', self.browser.contents
        )

    def test_files_with_spaces_removal(self):
        doc1 = self.portal.doc1

        self.portal.invokeFactory(
            "Document", id="some spaces.doc", title="A spaces doc"
        )
        spaces1 = self.portal["some spaces.doc"]
        set_text(doc1, '<a href="some spaces.doc">a document</a>')
        self.assertEqual([i.to_object for i in getOutgoingLinks(doc1)], [spaces1])
        transaction.commit()

        self.browser.handleErrors = True
        self.browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                spaces1.absolute_url(), self._get_token(spaces1)
            )
        )
        self.assertIn("Potential link breakage", self.browser.contents)
        self.assertIn(
            '<a href="http://nohost/plone/doc1">Test Page 1</a>', self.browser.contents
        )
        self.browser.getControl(name="form.buttons.Delete").click()
        self.assertNotIn("some spaces.doc", self.portal.objectIds())

    def test_warn_about_content(self):
        folder1 = self.portal.folder1
        self.browser.open(
            "{}/delete_confirmation?_authenticator={}".format(
                folder1.absolute_url(), self._get_token(folder1)
            )
        )
        self.assertIn("Number of selected", self.browser.contents)
        self.assertTrue(re.search(r"2\s+Objects in all", self.browser.contents))
        self.assertTrue(re.search(r"1\s+Folders", self.browser.contents))
        self.assertTrue(re.search(r"0\s+Published objects", self.browser.contents))

    def test_update(self):
        doc1 = self.portal.doc1
        doc2 = self.portal.doc2
        doc4 = self.portal.folder1.doc4

        set_text(doc1, '<a href="doc2">a document</a>')
        set_text(doc2, '<a href="folder1/doc4">a document</a>')

        catalog = getUtility(ICatalog)
        for rel in list(catalog.findRelations()):
            catalog.unindex(rel)

        self.assertEqual([i.to_object for i in getOutgoingLinks(doc1)], [])
        self.assertEqual([i.to_object for i in getOutgoingLinks(doc2)], [])

        transaction.commit()
        self.browser.open(
            f"{self.portal.absolute_url()}/updateLinkIntegrityInformation"
        )
        self.browser.getControl("Update").click()
        self.assertIn("Link integrity information updated for", self.browser.contents)

        self.assertEqual([i.to_object for i in getOutgoingLinks(doc1)], [doc2])
        self.assertEqual([i.to_object for i in getOutgoingLinks(doc2)], [doc4])
