from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import TEST_USER_ID
from plone.base.utils import unrestricted_construct_instance
from plone.testing import zope


class PloneAppLayoutFixture(PloneSandboxLayer):
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


PLONE_APP_LAYOUT_FIXTURE = PloneAppLayoutFixture()
PLONE_APP_LAYOUT_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONE_APP_LAYOUT_FIXTURE,),
    name="plone.app.layout:Integration",
)
PLONE_APP_LAYOUT_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONE_APP_LAYOUT_FIXTURE,),
    name="plone.app.layout:Functional",
)
PLONE_APP_LAYOUT_ROBOT_TESTING = FunctionalTesting(
    bases=(REMOTE_LIBRARY_BUNDLE_FIXTURE, zope.WSGI_SERVER_FIXTURE),
    name="plone.app.layout:Robot",
)
