from plone.app.layout.testing import PLONE_APP_LAYOUT_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer


class CMFEditionsFixture(PloneSandboxLayer):
    defaultBases = (PLONE_APP_LAYOUT_FIXTURE,)

    def setUpPloneSite(self, portal):
        # The built-in "plone.versioning" behavior auto-saves a version on
        # every edit, which would make the version numbering in these tests
        # unpredictable.  Disable it, like Products.CMFEditions' own test
        # fixture does, so only explicit applyVersionControl/save calls
        # create versions.
        for name in ("Document", "Event", "Link", "News Item"):
            fti = portal.portal_types[name]
            fti.behaviors = tuple(
                b
                for b in fti.behaviors
                if b
                not in (
                    "plone.app.versioningbehavior.behaviors.IVersionable",
                    "plone.versioning",
                )
            )


CMFEDITIONS_FIXTURE = CMFEditionsFixture()
CMFEDITIONS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(CMFEDITIONS_FIXTURE,),
    name="plone.app.layout:CMFEditionsIntegration",
)
