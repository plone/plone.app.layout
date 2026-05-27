from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.layout.outputfilters.caption_filter import (  # noqa
    IImageCaptioningEnabler,
)
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import TEST_USER_ID
from plone.base.utils import unrestricted_construct_instance
from zope.interface import implementer

import zope.component


class Fixture(PloneSandboxLayer):
    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import plone.app.layout

        self.loadZCML(package=plone.app.layout)

    def setUpPloneSite(self, portal):
        unrestricted_construct_instance("Folder", portal, id="Members")
        mtool = portal.portal_membership
        if not mtool.getMemberareaCreationFlag():
            mtool.setMemberareaCreationFlag()
        mtool.createMemberArea(TEST_USER_ID)
        if mtool.getMemberareaCreationFlag():
            mtool.setMemberareaCreationFlag()
        applyProfile(portal, "plone.app.layout:default")


FIXTURE = Fixture()
INTEGRATION_TESTING = IntegrationTesting(
    bases=(FIXTURE,),
    name="plone.app.layout:Integration",
)
FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FIXTURE,),
    name="plone.app.layout:Functional",
)


@implementer(IImageCaptioningEnabler)
class DummyImageCaptioningEnabler:
    available = True


class CaptionOutputfilters(PloneSandboxLayer):
    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import plone.outputfilters

        self.loadZCML(package=plone.outputfilters)
        gsm = zope.component.getGlobalSiteManager()
        gsm.registerUtility(
            DummyImageCaptioningEnabler(),
            IImageCaptioningEnabler,
            "outputfiltertest",
            event=False,
        )

    def tearDownZope(self, app):
        gsm = zope.component.getGlobalSiteManager()
        gsm.unregisterUtility(provided=IImageCaptioningEnabler, name="outputfiltertest")

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.outputfilters:default")


CAPTION_OUTPUTFILTERS_FIXTURE = CaptionOutputfilters()
CAPTION_OUTPUTFILTERS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(CAPTION_OUTPUTFILTERS_FIXTURE,), name="CaptionOutputfilters:Integration"
)
CAPTION_OUTPUTFILTERS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(CAPTION_OUTPUTFILTERS_FIXTURE,), name="CaptionOutputfilters:Functional"
)
