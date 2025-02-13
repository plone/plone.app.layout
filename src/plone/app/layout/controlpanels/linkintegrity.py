from Acquisition import aq_inner
from datetime import datetime
from datetime import timedelta
from OFS.interfaces import IFolder
from plone.app.linkintegrity.handlers import modifiedContent
from plone.app.linkintegrity.utils import getIncomingLinks
from plone.app.linkintegrity.utils import linkintegrity_enabled
from plone.base import PloneMessageFactory as _
from plone.base.interfaces import IPloneSiteRoot
from plone.uuid.interfaces import IUUID
from Products.CMFCore.permissions import AccessContentsInformation
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from transaction import savepoint
from zExceptions import NotFound
from zope.i18n import translate

import logging

logger = logging.getLogger(__name__)


class DeleteConfirmationInfo(BrowserView):
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

    def get_breaches(self, items=None):
        """Return breaches for multiple items.

        Breaches coming from objects in the list of items
        or their children (if a object is a folder) will be ignored.
        """
        if items is None:
            items = [self.context]
        catalog = getToolByName(self.context, "portal_catalog")
        results = []
        uids_to_ignore = set()
        self.breach_count = {}
        path2obj = dict()
        path2brains = dict()

        # build various helper structures
        for obj in items:
            obj_path = "/".join(obj.getPhysicalPath())
            path2obj[obj_path] = obj
            path2brains[obj_path] = brains_to_delete = catalog(path={"query": obj_path})
            # add the current items uid and all its children's uids to the
            # list of uids that are ignored
            uids_to_ignore.update([i.UID for i in brains_to_delete])

        excluded_paths = set(path2obj.keys())

        # determine breaches
        for obj_path, obj in path2obj.items():
            brains_to_delete = path2brains[obj_path]
            for brain_to_delete in brains_to_delete:
                try:
                    obj_to_delete = brain_to_delete.getObject()  # noqa
                except (AttributeError, KeyError):
                    logger.exception(
                        "No object found for %s! Skipping", brain_to_delete
                    )
                    continue
                # look into potential breach
                breach = self.check_object(
                    obj=obj_to_delete, excluded_paths=excluded_paths
                )
                if breach:
                    for source in breach["sources"]:
                        # Only add the breach if one the sources is not in the
                        # list of items that are to be deleted.
                        if source["uid"] not in uids_to_ignore:
                            results.append(breach)
                            break

            if IFolder.providedBy(obj):
                count = len(catalog(path={"query": obj_path}))
                count_dirs = len(catalog(path={"query": obj_path}, is_folderish=True))
                count_public = len(
                    catalog(path={"query": obj_path}, review_state="published")
                )
                if count:
                    self.breach_count[obj_path] = [count, count_dirs, count_public]

        return results

    def check_object(self, obj, excluded_path=None, excluded_paths=None):
        """Check one object for breaches.
        Breaches originating from excluded_paths are ignored.
        """
        # BBB: Support old and new parameters likewise
        if excluded_paths is None:
            excluded_paths = set()
        if excluded_path:
            excluded_paths.add(excluded_path)

        breaches = {}
        direct_links = getIncomingLinks(obj, from_attribute=None)
        has_breaches = False
        for direct_link in direct_links:
            source_path = direct_link.from_path
            if not source_path:
                # link is broken
                continue
            if any(
                [
                    source_path == excluded_path
                    or source_path.startswith(excluded_path + "/")
                    for excluded_path in excluded_paths
                ]
            ):
                # source is in excluded_path
                continue
            source = direct_link.from_object
            if not breaches.get("sources"):
                breaches["sources"] = []
            breaches["sources"].append(
                {
                    "uid": IUUID(source),
                    "title": source.Title(),
                    "url": source.absolute_url(),
                    "accessible": self.is_accessible(source),
                }
            )
            has_breaches = True
        if has_breaches:
            breaches["target"] = {
                "uid": IUUID(obj),
                "title": obj.Title(),
                "url": obj.absolute_url(),
                "portal_type": obj.portal_type,
                "type_title": self.get_portal_type_title(obj),
            }
            return breaches

    def get_portal_type_title(self, obj):
        """Get the portal type title of the object."""
        context = aq_inner(self.context)
        portal_types = getToolByName(context, "portal_types")
        fti = portal_types.get(obj.portal_type)
        if fti is not None:
            type_title_msgid = fti.Title()
        else:
            type_title_msgid = obj.portal_type
        type_title = translate(type_title_msgid, context=self.request)
        return type_title

    def is_accessible(self, obj):
        return _checkPermission(AccessContentsInformation, obj)

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
