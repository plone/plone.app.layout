from plone.app.content.testing import PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_PASSWORD
from plone.testing.zope import Browser

import transaction
import unittest

FOLDER = {
    "id": "testfolder",
    "title": "Test Folder",
    "description": "Test Folder Description",
}

DOCUMENT = {
    "id": "testdoc",
    "title": "Test Document",
    "description": "Test Document Description",
}

NEWSITEM = {
    "id": "testnews",
    "title": "Test News Item",
    "description": "Test News Item Description",
}


class SelectDefaultPageDXTestCase(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer["app"]
        self.portal = self.layer["portal"]
        self.portal.acl_users.userFolderAddUser(
            "editor", TEST_USER_PASSWORD, ["Editor"], []
        )

        self._create_structure()
        transaction.commit()

        self.browser = Browser(self.layer["app"])
        self.browser.addHeader(
            "Authorization", "Basic {}:{}".format("editor", TEST_USER_PASSWORD)
        )

    def tearDown(self):
        self.portal.manage_delObjects(ids=FOLDER["id"])
        transaction.commit()

    def _createFolder(self):
        self.portal.invokeFactory(id=FOLDER["id"], type_name="Folder")
        folder = getattr(self.portal, FOLDER["id"])
        folder.setTitle(FOLDER["title"])
        folder.setDescription(FOLDER["description"])
        folder.reindexObject()
        # we don't want it in the navigation
        # folder.setExcludeFromNav(True)
        return folder

    def _createDocument(self, context):
        context.invokeFactory(id=DOCUMENT["id"], type_name="Document")
        doc = getattr(context, DOCUMENT["id"])
        doc.setTitle(DOCUMENT["title"])
        doc.setDescription(DOCUMENT["description"])
        doc.reindexObject()
        # we don't want it in the navigation
        # doc.setExcludeFromNav(True)
        return doc

    def _createNewsItem(self, context):
        context.invokeFactory(id=NEWSITEM["id"], type_name="News Item")
        doc = getattr(context, NEWSITEM["id"])
        doc.setTitle(NEWSITEM["title"])
        doc.setDescription(NEWSITEM["description"])
        doc.reindexObject()
        # we don't want it in the navigation
        # doc.setExcludeFromNav(True)
        return doc

    def _create_structure(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        folder = self._createFolder()
        self._createDocument(folder)
        return folder

    def test_select_default_page_view(self):
        """Check that the form can be rendered."""
        folder = self.portal.testfolder

        self.browser.open("%s/@@select_default_page" % folder.absolute_url())

        self.assertTrue("Select default page" in self.browser.contents)
        self.assertTrue('id="testdoc"' in self.browser.contents)

    def test_select_default_page_vhm_hosted(self):
        # Install a Virtual Host Monster
        if "virtual_hosting" not in self.app.objectIds():
            # If ZopeLite was imported, we have no default virtual
            # host monster
            from Products.SiteAccess.VirtualHostMonster import (
                manage_addVirtualHostMonster,
            )

            manage_addVirtualHostMonster(self.app, "virtual_hosting")
        transaction.commit()

        folder = self.portal.testfolder
        folder_vhm_url = (
            "{}/VirtualHostBase/http/plone.org/{}/VirtualHostRoot/{}".format(
                self.app.absolute_url(),
                self.portal.id,
                folder.id,
            )
        )

        self.browser.open(f"{folder_vhm_url}/@@select_default_page")

        self.assertTrue("Select default page" in self.browser.contents)
        self.assertTrue('id="testdoc"' in self.browser.contents)

    def test_select_default_page_view_with_folderish_type(self):
        """Check if folderish types are available."""
        folder = self.portal.testfolder
        folder.invokeFactory(id=FOLDER["id"], type_name="Folder")
        folder2 = getattr(folder, FOLDER["id"])
        folder.setTitle(FOLDER["title"])
        folder2.reindexObject()
        folder_fti = self.portal.portal_types["Folder"]
        folder_fti.manage_changeProperties(
            filter_content_types=True, allowed_content_types=[]
        )
        view = folder.restrictedTraverse("@@select_default_page")()

        self.assertTrue('id="testdoc"' in view)
        self.assertTrue('id="testfolder"' in view)

    def test_default_page_action_cancel(self):
        """Check the Cancel action."""
        folder = self.portal.testfolder

        self.browser.open("%s/@@select_default_page" % folder.absolute_url())
        cancel_button = self.browser.getControl(name="form.buttons.Cancel")
        cancel_button.click()

        self.assertEqual(self.browser.url, folder.absolute_url())
        self.assertIs(folder.getDefaultPage(), None)

    def test_default_page_action_save(self):
        """Check the Save action."""
        folder = self.portal.testfolder
        self.browser.open("%s/@@select_default_page" % folder.absolute_url())

        submit_button = self.browser.getControl(name="form.buttons.Save")
        submit_button.click()

        self.assertEqual(self.browser.url, folder.absolute_url())
        self.assertEqual(folder.getDefaultPage(), "testdoc")

    def test_selectable_types_filter(self):
        self.portal.portal_registry["plone.default_page_types"] = ["News Item"]
        folder = self.portal.testfolder
        self._createNewsItem(folder)

        view = folder.restrictedTraverse("@@select_default_page")()
        self.assertTrue('id="testdoc"' not in view)
        self.assertTrue('id="testnews"' in view)
