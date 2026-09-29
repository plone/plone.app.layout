from plone.app.content.testing import PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.locking.interfaces import ILockable
from plone.testing.zope import Browser
from z3c.form.interfaces import IFormLayer
from zExceptions import NotFound
from zExceptions import Unauthorized
from zope.component import getMultiAdapter
from zope.interface import alsoProvides

import transaction
import unittest


class ActionsDXTestCase(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

        self.portal.acl_users.userFolderAddUser(
            "editor", TEST_USER_PASSWORD, ["Editor"], []
        )

        # For z3c.forms request must provide IFormLayer
        alsoProvides(self.request, IFormLayer)

        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory(type_name="Folder", id="f1", title="A Tést Folder")

        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )

    def tearDown(self):
        if "f1" in self.portal.objectIds():
            self.portal.manage_delObjects(ids="f1")
            transaction.commit()

    def test_delete_confirmation(self):
        folder = self.portal["f1"]

        form = getMultiAdapter((folder, self.request), name="delete_confirmation")
        form.update()

        cancel = form.buttons["Cancel"]
        form.handlers.getHandler(cancel)(form, form)

        self.assertFalse(form.is_locked)

    def test_delete_confirmation_if_locked(self):
        folder = self.portal["f1"]
        lockable = ILockable.providedBy(folder)

        form = getMultiAdapter((folder, self.request), name="delete_confirmation")
        form.update()

        self.assertFalse(form.is_locked)

        if lockable:
            lockable.lock()

        form = getMultiAdapter((folder, self.request), name="delete_confirmation")
        form.update()

        self.assertFalse(form.is_locked)

        # After switching the user it should not be possible to delete the
        # object. Of course this is only possible if our context provides
        # ILockable interface.
        if lockable:
            logout()
            login(self.portal, "editor")

            form = getMultiAdapter((folder, self.request), name="delete_confirmation")
            form.update()
            self.assertTrue(form.is_locked)

            logout()
            login(self.portal, TEST_USER_NAME)

            ILockable(folder).unlock()

    def test_delete_confirmation_cancel(self):
        folder = self.portal["f1"]

        self.browser.open(folder.absolute_url() + "/delete_confirmation")
        self.browser.getControl(name="form.buttons.Cancel").click()
        context_state = getMultiAdapter(
            (folder, self.request), name="plone_context_state"
        )
        self.assertEqual(self.browser.url, context_state.view_url())

    def prepare_for_acquisition_tests(self):
        """create content and an alternate authenticated browser session

        creates the following content structure:

        |-- f1
        |   |-- test
        |-- test
        """
        # create a page at the root and one nested with the same id.
        p1 = self.portal.invokeFactory(
            type_name="Document", id="test", title="Test Page at Root"
        )
        folder_1 = self.portal["f1"]
        p2 = folder_1.invokeFactory(
            type_name="Document", id="test", title="Test Page in Folder"
        )
        contained_test_page = folder_1[p2]

        transaction.commit()

        # create an alternate browser also logged in with manager
        browser_2 = Browser(self.layer["app"])
        browser_2.handleErrors = False
        browser_2.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )

        # return the id of the root page, the nested page itself, and the
        # alternate browser
        return p1, contained_test_page, browser_2

    def test_delete_wrong_object_by_acquisition_with_action(self):
        """exposes delete-by-acquisition bug using the delete action

        see https://github.com/plone/Products.CMFPlone/issues/383
        """
        p1_id, page_2, browser_2 = self.prepare_for_acquisition_tests()

        # open two different browsers to the 'delete confirmation' view
        delete_url = page_2.absolute_url() + "/delete_confirmation"
        self.browser.open(delete_url)
        browser_2.open(delete_url)
        self.assertTrue(p1_id in self.portal)

        # Try to delete in both browsers
        self.browser.getControl(name="form.buttons.Delete").click()
        try:
            browser_2.getControl(name="form.buttons.Delete").click()
        except NotFound:
            pass

        # the nested folder should be gone, but the one at the root should
        # remain.
        self.assertFalse(page_2.id in self.portal["f1"])
        self.assertTrue(p1_id in self.portal)

    def test_rename_form(self):
        logout()
        folder = self.portal["f1"]

        # We need zope2.CopyOrMove permission to rename content
        self.browser.open(folder.absolute_url() + "/folder_rename")
        self.browser.getControl(name="form.widgets.new_id").value = "f2"
        self.browser.getControl(name="form.widgets.new_title").value = "F2"
        self.browser.getControl(name="form.buttons.Rename").click()
        self.assertEqual(folder.getId(), "f2")
        self.assertEqual(folder.Title(), "F2")
        self.assertEqual(self.browser.url, folder.absolute_url())

        login(self.portal, TEST_USER_NAME)
        self.portal.manage_delObjects(ids="f2")
        transaction.commit()

    def test_rename_form_with_view_action(self):
        # can't be bothered to register blobs, instead we add documents to
        # typesUseViewActionInListings
        registry = self.portal.portal_registry
        registry["plone.types_use_view_action_in_listings"] = [
            "Image",
            "File",
            "Document",
        ]

        folder = self.portal["f1"]
        folder.invokeFactory("Document", "document1")
        document1 = folder["document1"]
        transaction.commit()
        logout()

        # We need zope2.CopyOrMove permission to rename content
        self.browser.open(document1.absolute_url() + "/object_rename")
        self.browser.getControl(name="form.widgets.new_id").value = "f2"
        self.browser.getControl(name="form.widgets.new_title").value = "F2"
        self.browser.getControl(name="form.buttons.Rename").click()
        self.assertEqual(document1.getId(), "f2")
        self.assertEqual(document1.Title(), "F2")
        self.assertEqual(self.browser.url, document1.absolute_url() + "/view")

        login(self.portal, TEST_USER_NAME)
        self.portal.manage_delObjects(ids="f1")
        transaction.commit()

    def test_create_safe_id_on_renaming(self):
        logout()
        folder = self.portal["f1"]

        # We need zope2.CopyOrMove permission to rename content
        self.browser.open(folder.absolute_url() + "/folder_rename")
        self.browser.getControl(name="form.widgets.new_id").value = " ? f4 4 "
        self.browser.getControl(name="form.widgets.new_title").value = " F2 "
        self.browser.getControl(name="form.buttons.Rename").click()
        self.assertEqual(folder.getId(), "f4-4")
        self.assertEqual(folder.Title(), "F2")
        self.assertEqual(self.browser.url, folder.absolute_url())

        login(self.portal, TEST_USER_NAME)
        self.portal.manage_delObjects(ids="f4-4")
        transaction.commit()

    def test_default_page_updated_on_rename(self):
        login(self.portal, TEST_USER_NAME)
        folder = self.portal["f1"]
        folder.invokeFactory(type_name="Document", id="d1", title="A Doc")
        doc = folder["d1"]
        folder.setDefaultPage("d1")
        transaction.commit()
        self.assertEqual(folder.getDefaultPage(), "d1")

        # We need zope2.CopyOrMove permission to rename content
        self.browser.open(doc.absolute_url() + "/object_rename")
        self.browser.getControl(name="form.widgets.new_id").value = " ?renamed"
        self.browser.getControl(name="form.widgets.new_title").value = "Doc"
        self.browser.getControl(name="form.buttons.Rename").click()
        self.assertEqual(folder.contentIds()[0], "renamed")
        self.assertEqual(folder.getDefaultPage(), "renamed")

    def test_rename_form_cancel(self):
        folder = self.portal["f1"]

        _id = folder.getId()
        _title = folder.Title()

        self.browser.open(folder.absolute_url() + "/folder_rename")
        self.browser.getControl(name="form.buttons.Cancel").click()
        transaction.commit()

        self.assertEqual(self.browser.url, folder.absolute_url())
        self.assertEqual(folder.getId(), _id)
        self.assertEqual(folder.Title(), _title)

    def test_rename_form_cancel_with_view_action(self):
        # can't be bothered to register blobs, instead we add documents to
        # typesUseViewActionInListings
        registry = self.portal.portal_registry
        registry["plone.types_use_view_action_in_listings"] = [
            "Image",
            "File",
            "Document",
        ]
        folder = self.portal["f1"]
        folder.invokeFactory("Document", "document1")
        document1 = folder["document1"]
        transaction.commit()

        _id = document1.getId()
        _title = document1.Title()

        self.browser.open(document1.absolute_url() + "/object_rename")
        self.browser.getControl(name="form.buttons.Cancel").click()
        transaction.commit()

        self.assertEqual(self.browser.url, document1.absolute_url() + "/view")
        self.assertEqual(document1.getId(), _id)
        self.assertEqual(document1.Title(), _title)

    def _get_token(self, context):
        authenticator = getMultiAdapter((context, self.request), name="authenticator")

        return authenticator.token()

    def test_object_cut_view(self):
        folder = self.portal["f1"]

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{folder.absolute_url():s}/object_cut"
        )

        # We need to have Copy or Move permission to cut an object
        self.browser.open(
            "{:s}/object_cut?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(folder)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.assertIn(f"{folder.Title():s} cut.", self.browser.contents)

    def test_object_cut_view_with_view_action(self):
        # can't be bothered to register blobs, instead we add documents to
        # typesUseViewActionInListings
        registry = self.portal.portal_registry
        registry["plone.types_use_view_action_in_listings"] = [
            "Image",
            "File",
            "Document",
        ]
        folder = self.portal["f1"]
        folder.invokeFactory("Document", "document1")
        document1 = folder["document1"]
        transaction.commit()

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{document1.absolute_url():s}/object_cut"
        )

        # We need to have Copy or Move permission to cut an object
        self.browser.open(
            "{:s}/object_cut?_authenticator={:s}".format(
                document1.absolute_url(), self._get_token(document1)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.assertIn(f"{document1.Title():s} cut.", self.browser.contents)
        self.assertEqual(document1.absolute_url() + "/view", self.browser.url)

    def test_object_copy_view(self):
        folder = self.portal["f1"]

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{folder.absolute_url():s}/object_copy"
        )

        self.browser.open(
            "{:s}/object_copy?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(folder)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.assertIn(f"{folder.Title():s} copied.", self.browser.contents)

    def test_object_copy_with_view_action(self):
        # can't be bothered to register blobs, instead we add documents to
        # typesUseViewActionInListings
        registry = self.portal.portal_registry
        registry["plone.types_use_view_action_in_listings"] = [
            "Image",
            "File",
            "Document",
        ]

        folder = self.portal["f1"]
        folder.invokeFactory("Document", "document1")
        document1 = folder["document1"]
        transaction.commit()

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{document1.absolute_url():s}/object_copy"
        )

        self.browser.open(
            "{:s}/object_copy?_authenticator={:s}".format(
                document1.absolute_url(), self._get_token(document1)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.assertIn(f"{document1.Title():s} copied.", self.browser.contents)
        self.assertEqual(document1.absolute_url() + "/view", self.browser.url)

    def test_object_cut_and_paste(self):
        folder = self.portal["f1"]
        self.portal.invokeFactory(type_name="Document", id="d1", title="A Doc")
        doc = self.portal["d1"]
        transaction.commit()

        self.browser.open(
            "{:s}/object_cut?_authenticator={:s}".format(
                doc.absolute_url(), self._get_token(doc)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.assertIn("d1", self.portal.objectIds())
        self.assertIn("f1", self.portal.objectIds())

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{folder.absolute_url():s}/object_paste"
        )

        self.browser.open(
            "{:s}/object_paste?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(doc)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        transaction.commit()

        self.assertNotIn("d1", self.portal.objectIds())
        self.assertIn("d1", folder.objectIds())
        self.assertIn("Item(s) pasted.", self.browser.contents)

    def test_object_copy_and_paste(self):
        folder = self.portal["f1"]
        folder.invokeFactory(type_name="Document", id="d1", title="A Doc")
        doc = folder["d1"]
        transaction.commit()

        self.browser.open(
            "{:s}/object_copy?_authenticator={:s}".format(
                doc.absolute_url(), self._get_token(doc)
            )
        )

        self.assertIn("__cp", self.browser.cookies)

        # We need pass an authenticator token to prevent Unauthorized
        self.assertRaises(
            Unauthorized, self.browser.open, f"{folder.absolute_url():s}/object_paste"
        )

        self.browser.open(
            "{:s}/object_paste?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(folder)
            )
        )
        transaction.commit()

        self.assertIn("f1", self.portal.objectIds())
        self.assertIn("d1", folder.objectIds())
        self.assertIn("copy_of_d1", folder.objectIds())
        self.assertIn("Item(s) pasted.", self.browser.contents)

    def test_object_copy_and_paste_multiple_times(self):
        folder = self.portal["f1"]
        folder.invokeFactory(type_name="Document", id="d1", title="A Doc")
        doc = folder["d1"]
        transaction.commit()

        self.browser.open(
            "{:s}/object_copy?_authenticator={:s}".format(
                doc.absolute_url(), self._get_token(doc)
            )
        )

        self.assertIn("__cp", self.browser.cookies)
        self.browser.open(
            "{:s}/object_paste?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(folder)
            )
        )
        self.browser.open(
            "{:s}/object_paste?_authenticator={:s}".format(
                folder.absolute_url(), self._get_token(folder)
            )
        )

        # Cookie should persist, because you can paste the item multiple times
        self.assertIn("__cp", self.browser.cookies)
        self.assertIn("f1", self.portal.objectIds())
        self.assertIn("d1", folder.objectIds())
        self.assertIn("copy_of_d1", folder.objectIds())
        self.assertIn("copy2_of_d1", folder.objectIds())
        self.assertIn("Item(s) pasted.", self.browser.contents)
