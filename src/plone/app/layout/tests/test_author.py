from AccessControl import Unauthorized
from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID
from plone.base.interfaces import ISecuritySchema
from plone.registry.interfaces import IRegistry
from zope.component import getMultiAdapter
from zope.component import getUtility

import unittest
import warnings


class TestAuthorView(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def get_view(self, username=TEST_USER_ID):
        view = getMultiAdapter((self.portal, self.request), name="author")
        return view.publishTraverse(self.request, username)

    def test_using_correct_template(self):
        """Ensure that the author view uses the template from plone.app.layout."""
        view = getMultiAdapter((self.portal, self.request), name="author")
        self.assertIn(
            "plone/app/layout/views/templates/author.pt", view.index.filename
        )

    def test_render(self):
        view = self.get_view()
        self.assertEqual(view.username, TEST_USER_ID)
        result = view()
        self.assertIn(TEST_USER_ID, result)
        # The feedback form is not shown to the owner of the page.
        self.assertTrue(view.is_owner)

    def test_anonymous_unauthorized(self):
        registry = getUtility(IRegistry)
        security_settings = registry.forInterface(ISecuritySchema, prefix="plone")
        security_settings.allow_anon_views_about = False
        logout()
        view = self.get_view()
        with self.assertRaises(Unauthorized):
            view()


class TestAuthorDeprecatedImports(unittest.TestCase):
    def test_old_imports(self):
        """The old imports from Products.CMFPlone still work."""
        from plone.app.layout.views import author
        from plone.app.layout.views import interfaces

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from Products.CMFPlone.browser.author import AuthorFeedbackForm
            from Products.CMFPlone.browser.author import AuthorView
            from Products.CMFPlone.browser.interfaces import IAuthorFeedbackForm

        self.assertIs(AuthorView, author.AuthorView)
        self.assertIs(AuthorFeedbackForm, author.AuthorFeedbackForm)
        self.assertIs(IAuthorFeedbackForm, interfaces.IAuthorFeedbackForm)
