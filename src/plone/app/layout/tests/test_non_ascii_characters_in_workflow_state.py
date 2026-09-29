from plone.app.content.testing import PLONE_APP_CONTENT_NON_ASCII_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.uuid.interfaces import IUUID
from Products.CMFCore.utils import getToolByName

import json
import unittest


class TestNonAsciiCharactersWorkflow(unittest.TestCase):
    layer = PLONE_APP_CONTENT_NON_ASCII_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        # set non-ascii-workflow for Documents
        wf_tool = getToolByName(self, "portal_workflow")
        wf_tool.setChainForPortalTypes(["Document"], "non-ascii-workflow")

        # create an object having the non-ascii-workflow assigned
        self.portal.invokeFactory("Document", "doc")

    def test_non_ascii_characters_in_workflow_title(self):
        wf_tool = getToolByName(self, "portal_workflow")
        workflow_matching_id = list(
            filter(
                lambda workflow: ("non-ascii-workflow" in workflow.id),
                wf_tool.getWorkflowsFor(self.portal.doc),
            )
        )

        # Make sure that the non-ascii-workflow was assigned to the Document
        self.assertTrue(workflow_matching_id)

        # Build POST request to get state title for the Document
        documents_uid = IUUID(self.portal.doc)
        self.request.form["selection"] = json.dumps(documents_uid)
        self.request.form["transitions"] = True
        self.request.form["render"] = "yes"

        try:
            # try to do the json request which among other things returns
            # the workflow state title containing non-ascii characters.
            self.portal.unrestrictedTraverse("@@fc-workflow")()
        except UnicodeDecodeError:
            self.fail("Calling @@fc-workflow raised UnicodeDecodeError \
                       unexpectedly.")
