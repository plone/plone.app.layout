from plone.app.content.testing import PLONE_APP_CONTENT_DX_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.base.utils import is_expired
from zExceptions import Forbidden
from zope.component import getMultiAdapter

import unittest


class TestContentPublishing(unittest.TestCase):
    """Test the recursive behaviour of folder_publish.

    Adapted from CMFPlone/tests/testContentPublishing.py.
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
        self.folder.invokeFactory("Folder", id="f1", title="Folder 1")
        self.folder.f1.invokeFactory("Document", id="d2", title="Doc 2")
        self.folder.f1.invokeFactory("Folder", id="f2", title="Folder 2")

    def setup_authenticator(self):
        from plone.protect.authenticator import createToken

        self.request.form["_authenticator"] = createToken()

    def test_folder_publish_get(self, **kwargs):
        self.setup_authenticator()
        view = getMultiAdapter((self.folder, self.request), name="folder_publish")
        with self.assertRaises(Forbidden):
            view(**kwargs)

    def test_folder_publish_post_without_authenticator(self, **kwargs):
        self.request.environ["REQUEST_METHOD"] = "POST"
        # request.set("REQUEST_METHOD", "POST")
        view = getMultiAdapter((self.folder, self.request), name="folder_publish")
        with self.assertRaises(Forbidden):
            view(**kwargs)

    def folder_publish(self, **kwargs):
        self.request.set("REQUEST_METHOD", "POST")
        self.setup_authenticator()
        view = getMultiAdapter((self.folder, self.request), name="folder_publish")
        return view(**kwargs)

    def test_initial_state(self):
        # Depending on the Plone version,
        # the review state may be visible or private.  Check which one it is.
        for o in (self.folder.d1, self.folder.f1, self.folder.f1.d2, self.folder.f1.f2):
            self.assertEqual(self.workflow.getInfoFor(o, "review_state"), "private")

    def test_publishing_subobjects(self):
        paths = []
        for o in (self.folder.d1, self.folder.f1):
            paths.append("/".join(o.getPhysicalPath()))

        self.folder_publish(
            workflow_action="publish", paths=paths, include_children=True
        )
        for o in (self.folder.d1, self.folder.f1, self.folder.f1.d2, self.folder.f1.f2):
            self.assertEqual(self.workflow.getInfoFor(o, "review_state"), "published")
        self.assertEqual(self.request.response.getStatus(), 302)
        self.assertEqual(
            self.request.response.getHeader("Location"), self.folder.absolute_url()
        )

    def test_publishing_subobjects_and_expire_them(self):
        paths = []
        for o in (self.folder.d1, self.folder.f1):
            paths.append("/".join(o.getPhysicalPath()))

        self.folder_publish(
            workflow_action="publish",
            paths=paths,
            effective_date="1/1/2001",
            expiration_date="1/2/2001",
            include_children=True,
        )
        for o in (self.folder.d1, self.folder.f1, self.folder.f1.d2, self.folder.f1.f2):
            self.assertEqual(self.workflow.getInfoFor(o, "review_state"), "published")
            self.assertTrue(is_expired(o))

    def test_publishing_without_subobjects(self):
        paths = []
        for o in (self.folder.d1, self.folder.f1):
            paths.append("/".join(o.getPhysicalPath()))

        self.folder_publish(
            workflow_action="publish", paths=paths, include_children=False
        )
        for o in (self.folder.d1, self.folder.f1):
            self.assertEqual(self.workflow.getInfoFor(o, "review_state"), "published")
        for o in (self.folder.f1.d2, self.folder.f1.f2):
            self.assertEqual(self.workflow.getInfoFor(o, "review_state"), "private")

    def test_publishing_orig_template_safe(self):
        paths = []
        for o in (self.folder.d1, self.folder.f1):
            paths.append("/".join(o.getPhysicalPath()))

        self.request.form["orig_template"] = "some_view"
        self.folder_publish(workflow_action="publish", paths=paths)
        self.assertEqual(self.request.response.getHeader("Location"), "some_view")

    def test_publishing_orig_template_attacker(self):
        paths = []
        for o in (self.folder.d1, self.folder.f1):
            paths.append("/".join(o.getPhysicalPath()))

        self.request.form["orig_template"] = "https://attacker.com"
        self.folder_publish(workflow_action="publish", paths=paths)
        self.assertEqual(
            self.request.response.getHeader("Location"), self.folder.absolute_url()
        )
