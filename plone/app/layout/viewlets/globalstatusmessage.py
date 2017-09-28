# -*- coding: utf-8 -*-
from plone.app.layout.viewlets.common import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage

try:
    from Products.CMFPlone.utils import get_top_request
except ImportError:
    get_top_request = None


class GlobalStatusMessage(ViewletBase):
    """Display messages to the current user"""

    index = ViewPageTemplateFile('globalstatusmessage.pt')

    def update(self):
        super(GlobalStatusMessage, self).update()
        request = self.request
        request = get_top_request(request) if get_top_request else request
        self.status = IStatusMessage(request)
        self.messages = self.status.show()
