from plone.app.content.testing import PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING
from plone.app.content.testing import PLONE_APP_CONTENT_DX_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.base.utils import is_expired
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.testing.zope import Browser
from zope.component import getMultiAdapter

import os
import transaction
import unittest


class TestContentStatusModifyIntegration(unittest.TestCase):
    """The the content_status_modify view.

    Until and including Plone 5.2, this was a skin script in Products.CMFPlone.
    Tests adapted from CMFPlone/tests/testContentPublishing.py.
    """

    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        self.workflow = self.portal.portal_workflow
        # Make sure we can create and publish directly.
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        # Prepare content.
        self.portal.invokeFactory("Folder", id="folder")
        self.folder = self.portal.folder
        self.folder.invokeFactory("Document", id="d1", title="Doc 1")

    def setup_authenticator(self):
        from plone.protect.authenticator import createToken

        self.request.form["_authenticator"] = createToken()

    def get_content_status_modify_view(self, obj):
        self.setup_authenticator()
        view = getMultiAdapter((obj, self.request), name="content_status_modify")
        return view

    # Test the recursive behaviour of content_status_modify:

    def testPublishingNonDefaultPageLeavesFolderAlone(self):
        view = self.get_content_status_modify_view(self.folder.d1)
        view("publish")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder, "review_state"), "private"
        )
        self.assertEqual(
            self.workflow.getInfoFor(self.folder.d1, "review_state"), "published"
        )

    def testPublishingDefaultPagePublishesFolder(self):
        self.folder.setDefaultPage("d1")
        view = self.get_content_status_modify_view(self.folder.d1)
        view("publish")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder, "review_state"), "published"
        )
        self.assertEqual(
            self.workflow.getInfoFor(self.folder.d1, "review_state"), "published"
        )

    def testPublishingDefaultPageWhenFolderCannotBePublished(self):
        self.folder.setDefaultPage("d1")
        # make parent be published already when publishing its default document
        # results in an attempt to do it again
        view = self.get_content_status_modify_view(self.folder)
        view("publish")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder, "review_state"), "published"
        )
        view = self.get_content_status_modify_view(self.folder.d1)
        view("publish")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder, "review_state"), "published"
        )
        self.assertEqual(
            self.workflow.getInfoFor(self.folder.d1, "review_state"), "published"
        )

    # test setting effective/expiration date and isExpired method

    def testIsExpiredWithExplicitExpiredContent(self):
        view = self.get_content_status_modify_view(self.folder.d1)
        view(
            workflow_action="publish",
            effective_date="1/1/2001",
            expiration_date="1/2/2001",
        )
        self.assertTrue(is_expired(self.folder.d1))

    def testIsExpiredWithExplicitNonExpiredContent(self):
        view = self.get_content_status_modify_view(self.folder.d1)
        view(workflow_action="publish")
        self.assertFalse(is_expired(self.folder.d1))

    def testEditorCanSubmitButNotPublish(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        self.folder.invokeFactory("Document", id="d2", title="Doc 2")
        view = self.get_content_status_modify_view(self.folder.d2)
        view(workflow_action="submit")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder.d2, "review_state"), "pending"
        )

        # Now try publishing.
        # For various reasons, there are no complaints/errors when trying
        # a transition that you are not allowed to do.
        view = self.get_content_status_modify_view(self.folder.d2)
        view(workflow_action="publish")
        self.assertEqual(
            self.workflow.getInfoFor(self.folder.d2, "review_state"), "pending"
        )


class TestContentStatusModifyFunctional(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        # Set workflow for files and images.
        wf_tool = self.portal.portal_workflow
        wf_tool.setChainForPortalTypes(["File"], "simple_publication_workflow")
        wf_tool.setChainForPortalTypes(["Image"], "simple_publication_workflow")

        # Create content.
        filename = os.path.join(os.path.dirname(__file__), "image.png")
        with open(filename, "rb") as f:
            FILE_DATA = f.read()
        self.portal.invokeFactory("Document", id="d1", title="Doc 1")
        self.portal.invokeFactory(
            "File",
            id="f1",
            title="File 1",
            file=NamedBlobFile(data=FILE_DATA, filename="image.png"),
        )
        self.portal.invokeFactory(
            "Image",
            id="i1",
            title="Image 1",
            image=NamedBlobImage(data=FILE_DATA, filename="image.png"),
        )
        self.portal_url = self.portal.absolute_url()
        transaction.commit()

        # Setup the test browser.
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.raiseHttpErrors = False
        self.browser.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )

    def test_history_doc(self):
        self.browser.open(f"{self.portal_url}/d1/content_status_history")
        self.browser.getControl("Save").click()
        self.assertEqual(self.browser.url, f"{self.portal_url}/d1")

    def test_history_file(self):
        self.browser.open(f"{self.portal_url}/f1/content_status_history")
        self.browser.getControl("Save").click()
        self.assertEqual(self.browser.url, f"{self.portal_url}/f1/view")

    def test_history_image(self):
        self.browser.open(f"{self.portal_url}/i1/content_status_history")
        self.browser.getControl("Save").click()
        self.assertEqual(self.browser.url, f"{self.portal_url}/i1/view")
