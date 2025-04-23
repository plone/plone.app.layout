from Acquisition import aq_inner
from datetime import datetime
from datetime import timedelta
from plone.app.linkintegrity.browser.info import (
    DeleteConfirmationInfo as DeleteConfirmationInfoAPI,
)
from plone.app.linkintegrity.handlers import modifiedContent
from plone.app.linkintegrity.utils import linkintegrity_enabled
from plone.base import PloneMessageFactory as _
from plone.base.interfaces import IPloneSiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from transaction import savepoint
from zExceptions import NotFound

import logging


logger = logging.getLogger(__name__)


class DeleteConfirmationInfo(DeleteConfirmationInfoAPI):
    template = ViewPageTemplateFile("linkintegrity_delete_confirmation_info.pt")
    breach_count = {}

    def __init__(self, context, request):
        self.linkintegrity_enabled = linkintegrity_enabled()
        self.context = context
        self.request = request

    def __call__(self, items=None):
        if not self.linkintegrity_enabled:
            return
        if items is None:
            if IPloneSiteRoot.providedBy(self.context):
                # Checking the portal for breaches makes no sense.
                return
            else:
                items = [self.context]
        self.breaches = self.get_breaches(items)
        return self.template()

    def objects(self):
        return [_("Objects in all"), _("Folders"), _("Published objects")]


class UpdateView(BrowserView):
    """Iterate over all catalogued items and update linkintegrity-information."""

    def __call__(self):
        context = aq_inner(self.context)
        request = aq_inner(self.request)
        if "update" in request.form or "delete_all" in request.form:
            starttime = datetime.now()
            count = self.update()
            duration = timedelta(seconds=(datetime.now() - starttime).seconds)
            msg = _(
                "linkintegrity_update_info",
                default="Link integrity information updated for ${count} "
                + "items in ${time} seconds.",
                mapping={"count": count, "time": str(duration)},
            )
            IStatusMessage(request).add(msg, type="info")
            msg = "Updated {} items in {} seconds".format(
                count,
                str(duration),
            )
            logger.info(msg)
            request.RESPONSE.redirect(getToolByName(context, "portal_url")())
        elif "cancel" in request.form:
            msg = _("Update cancelled.")
            IStatusMessage(request).add(msg, type="info")
            request.RESPONSE.redirect(getToolByName(context, "portal_url")())
        else:
            return self.index()

    def update(self):
        catalog = getToolByName(self.context, "portal_catalog")
        count = 0

        for brain in catalog():
            try:
                obj = brain.getObject()
            except (AttributeError, NotFound, KeyError):
                msg = "Catalog inconsistency: {0} not found!"
                logger.error(msg.format(brain.getPath()), exc_info=1)
                continue
            try:
                modifiedContent(obj, "dummy event parameter")
                count += 1
            except Exception:
                msg = "Error updating linkintegrity-info for {0}."
                logger.error(msg.format(obj.absolute_url()), exc_info=1)
            if count % 1000 == 0:
                savepoint(optimistic=True)
        return count
