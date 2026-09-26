from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.base.interfaces.controlpanel import IMailSchema
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.browser.author import AuthorFeedbackForm
from Products.CMFPlone.tests.utils import MockMailHost
from Products.MailHost.interfaces import IMailHost
from zope.component import getMultiAdapter
from zope.component import getSiteManager
from zope.component import getUtility

import unittest


class TestAuthorFeedbackTemplate(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_using_correct_template(self):
        """Ensure that the author-feedback-template view uses the template
        from plone.app.layout."""
        view = getMultiAdapter(
            (self.portal, self.request), name="author-feedback-template"
        )
        self.assertIn(
            "plone/app/layout/views/templates/author_feedback_template.pt",
            view.index.filename,
        )

    def test_render(self):
        view = getMultiAdapter(
            (self.portal, self.request), name="author-feedback-template"
        )
        result = view(
            message="Hello author",
            email_from_name="Plone site",
            sender_id="Jane (jane), jane@plone.test",
            url="http://nohost/plone/page",
            encoding="utf-8",
        )
        self.assertIn("Hello author", result)
        self.assertIn("Plone site", result)
        self.assertIn("http://nohost/plone/page", result)


class TestAuthorFeedbackForm(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

        registry = getUtility(IRegistry)
        mail_settings = registry.forInterface(IMailSchema, prefix="plone")
        mail_settings.email_from_address = "site@plone.test"
        mail_settings.email_from_name = "Plone site"

        member = self.portal.portal_membership.getMemberById(TEST_USER_ID)
        member.setMemberProperties({"email": "sender@plone.test"})
        # Log in again, so that the current user gets the new email.
        login(self.portal, TEST_USER_NAME)

        self.mailhost = MockMailHost("MailHost")
        sm = getSiteManager(self.portal)
        self.original_mailhost = sm.getUtility(IMailHost)
        sm.registerUtility(self.mailhost, provided=IMailHost)

    def tearDown(self):
        sm = getSiteManager(self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(self.original_mailhost, provided=IMailHost)

    def test_send_feedback_mail(self):
        """The author feedback form renders its mail with the template
        from plone.app.layout."""
        self.request.form.update(
            {
                "form.widgets.subject": "Feedback",
                "form.widgets.message": "Hello author",
                "form.widgets.author": TEST_USER_ID,
                "form.widgets.referer": "http://nohost/plone/page",
                "form.buttons.send": "Send",
            }
        )
        form = AuthorFeedbackForm(self.portal, self.request)
        form.update()

        self.assertEqual(len(self.mailhost.messages), 1)
        message = self.mailhost.messages[0]
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        self.assertIn("Hello author", message)
        self.assertIn("sender@plone.test", message)
