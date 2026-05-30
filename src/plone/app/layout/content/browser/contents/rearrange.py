from OFS.interfaces import IOrderedContainer
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.utils import json_loads
from plone.base import PloneMessageFactory as _
from plone.base.interfaces import IPloneSiteRoot
from plone.folder.interfaces import IExplicitOrdering
from Products.CMFCore.utils import getToolByName


class OrderContentsBaseAction(ContentsBaseAction):
    def getOrdering(self):
        if IPloneSiteRoot.providedBy(self.context):
            return self.context
        try:
            if self.context.aq_base.getOrdering():
                ordering = self.context.getOrdering()
            else:
                return None
        except AttributeError:
            if IOrderedContainer.providedBy(self.context):
                # Archetype
                return IOrderedContainer(self.context)
            return None
        if not IExplicitOrdering.providedBy(ordering):
            return None
        return ordering


class ItemOrderActionView(OrderContentsBaseAction):
    success_msg = _("Successfully moved item")
    failure_msg = _("Error moving item")

    def __call__(self):
        self.errors = []
        self.protect()
        id = self.request.form.get("id")
        ordering = self.getOrdering()

        if ordering is None:
            self.errors.append(_("This folder does not support ordering"))
            return self.message()

        delta = self.request.form["delta"]

        if delta == "top":
            ordering.moveObjectsToTop([id])
            return self.message()

        if delta == "bottom":
            ordering.moveObjectsToBottom([id])
            return self.message()

        delta = int(delta)
        subset_ids = json_loads(self.request.form.get("subsetIds", "null"))
        if subset_ids:
            position_id = [(ordering.getObjectPosition(i), i) for i in subset_ids]
            position_id.sort()
            if subset_ids != [i for position, i in position_id]:
                self.errors.append(_("Client/server ordering mismatch"))
                return self.message()

        ordering.moveObjectsByDelta([id], delta, subset_ids)
        return self.message()


class RearrangeActionView(OrderContentsBaseAction):
    success_msg = _("Successfully rearranged folder")
    failure_msg = _("Can not rearrange folder")

    def __call__(self):
        self.protect()
        self.errors = []
        ordering = self.getOrdering()
        if ordering:
            catalog = getToolByName(self.context, "portal_catalog")
            query = {
                "path": {"query": "/".join(self.context.getPhysicalPath()), "depth": 1},
                "sort_on": self.request.form.get("rearrange_on"),
                "show_inactive": True,
            }
            brains = catalog(**query)
            if self.request.form.get("reversed") == "true":
                brains = [b for b in reversed(brains)]
            for idx, brain in enumerate(brains):
                ordering.moveObjectToPosition(brain.id, idx)
        else:
            self.errors.append(_("Not explicit orderable"))
        return self.message()
