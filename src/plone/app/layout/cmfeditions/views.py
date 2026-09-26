from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

import os


class VersionsHistoryForm(BrowserView):
    def checkUpToDate(self, history):
        """Check if Up To Date.

        This used to be a Script (Python): checkUpToDate
        """
        repo = getToolByName(self.context, "portal_repository", None)

        isModified = None
        reverted_vid = None
        isReverted = None

        version_id = getattr(self.context, "version_id", None)
        if repo is not None:
            if version_id is None:
                isModified = True
                isReverted = False
            else:
                isModified = not repo.isUpToDate(self.context, version_id)
                historyLength = len(history)
                reverted_vid = version_id
                if historyLength == version_id + 1:
                    isReverted = False
                else:
                    isReverted = True
                if isModified:
                    version_id = historyLength

        return {
            "isModified": isModified,
            "version_id": version_id,
            "isReverted": isReverted,
            "reverted_vid": reverted_vid,
        }

    def can_diff(self):
        """Return True if content is diffable"""
        context = self.context
        portal_diff = getToolByName(context, "portal_diff", None)
        return (
            portal_diff
            and len(portal_diff.getDiffForPortalType(context.portal_type)) > 0
        )


css_path = os.path.join(os.path.dirname(__file__), "compare.css")
with open(css_path) as myfile:
    COMPARE_CSS = myfile.read()


class CompareCSS(BrowserView):
    """Formerly skins/CMFEditions/compare.css.dtml

    Should be a browser resource, but I don't want to change plone.app.iterate just now.
    That will further complicate an already complex PR.
    """

    def __call__(self):
        return COMPARE_CSS
