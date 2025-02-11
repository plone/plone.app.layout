from plone.protect.interfaces import IConfirmView
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from zExceptions import Forbidden
from zope.interface import implementer


@implementer(IConfirmView)
class ConfirmView(BrowserView):
    def __call__(self):
        urltool = getToolByName(self.context, "portal_url")
        original_url = getattr(self.request, "original_url", "")
        if not original_url or not urltool.isURLInPortal(original_url):
            raise Forbidden(f"url not in portal: {original_url}")
        return self.index()
