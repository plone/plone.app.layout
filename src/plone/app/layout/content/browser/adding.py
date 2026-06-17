from Acquisition import Implicit
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.adding import ContentAdding


class CMFAdding(Implicit, ContentAdding):
    """An adding view with a less silly next-url"""

    # We need to do this to get proper traversal URLs - otherwise, the
    # <base /> tag is messed up.
    id = "+"

    def add(self, content):
        content = super().add(content)
        # We need to ensure that we finish type construction, not at least
        # to set the correct permissions based on the workflow
        getToolByName(content, "portal_types")

        return content

    def nextURL(self):
        return f"{self.context.absolute_url()}/{self.contentName}/view"
