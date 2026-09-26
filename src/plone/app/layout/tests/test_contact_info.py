from plone.app.layout.testing import PLONE_APP_LAYOUT_FIXTURE
from plone.app.layout.testing import PLONE_APP_LAYOUT_FUNCTIONAL_TESTING
from plone.app.testing import FunctionalTesting
from plone.app.testing import MOCK_MAILHOST_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.base.interfaces.controlpanel import IMailSchema
from plone.registry.interfaces import IRegistry
from plone.testing import layered
from plone.testing.zope import Browser
from zope.component import getUtility

import doctest
import transaction
import unittest

OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE


class MockConfiguredMailHostLayer(PloneSandboxLayer):
    defaultBases = (
        MOCK_MAILHOST_FIXTURE,
        PLONE_APP_LAYOUT_FIXTURE,
    )

    def setUpPloneSite(self, portal):
        registry = getUtility(IRegistry)
        mail_settings = registry.forInterface(IMailSchema, prefix="plone")
        mail_settings.email_from_address = "mail@plone.test"


MOCK_CONFIGURED_MAILHOST_FIXTURE = MockConfiguredMailHostLayer()
MOCK_MAILHOST_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(MOCK_CONFIGURED_MAILHOST_FIXTURE,),
    name="plone.app.layout:MockMailHostFunctional",
)


class TestContactInfoNoMailHost(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        registry = getUtility(IRegistry)
        mail_settings = registry.forInterface(IMailSchema, prefix="plone")
        mail_settings.email_from_address = ""
        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False

    def test_no_mail_setup_message(self):
        self.browser.open(self.portal.absolute_url() + "/contact-info")
        self.assertIn("valid email setup", self.browser.contents)
        self.assertNotIn("form.buttons.send", self.browser.contents)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(__name__))
    suite.addTest(
        layered(
            doctest.DocFileSuite(
                "contact_info.txt",
                optionflags=OPTIONFLAGS,
                package="plone.app.layout.tests",
            ),
            layer=MOCK_MAILHOST_FUNCTIONAL_TESTING,
        )
    )
    return suite
