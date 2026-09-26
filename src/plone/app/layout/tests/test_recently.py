from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.component import getMultiAdapter

import unittest


class TestRecentlyViews(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory("Document", "private-doc", title="Private doc")
        self.portal.invokeFactory("Document", "public-doc", title="Public doc")
        self.portal.portal_workflow.doActionFor(self.portal["public-doc"], "publish")

    def get_view(self, name):
        return getMultiAdapter((self.portal, self.request), name=name)

    def render_content(self, name):
        """Render the view, and return only the content-core part.
        The rest of the page (for example the navigation) also shows items."""
        result = self.get_view(name)()
        return result[result.index('id="content-core"') :]

    def test_recently_modified_using_correct_template(self):
        """Ensure that the recently_modified view uses the template from
        plone.app.layout."""
        self.assertIn(
            "plone/app/layout/views/templates/recently_modified.pt",
            self.get_view("recently_modified").index.filename,
        )

    def test_recently_published_using_correct_template(self):
        """Ensure that the recently_published view uses the template from
        plone.app.layout."""
        self.assertIn(
            "plone/app/layout/views/templates/recently_published.pt",
            self.get_view("recently_published").index.filename,
        )

    def test_recently_modified_render(self):
        result = self.render_content("recently_modified")
        self.assertIn("Private doc", result)
        self.assertIn("Public doc", result)

    def test_recently_published_render(self):
        result = self.render_content("recently_published")
        self.assertNotIn("Private doc", result)
        self.assertIn("Public doc", result)
