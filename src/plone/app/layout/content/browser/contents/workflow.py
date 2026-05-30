from DateTime import DateTime
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.interfaces import IStructureAction
from plone.base import PloneMessageFactory as _
from plone.base.defaultpage import check_default_page_via_view
from plone.base.utils import safe_text
from Products.CMFCore.interfaces._content import IFolderish
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from ZODB.POSException import ConflictError
from zope.i18n import translate
from zope.interface import implementer


@implementer(IStructureAction)
class WorkflowAction:
    template = ViewPageTemplateFile("templates/workflow.pt")
    order = 7

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_options(self):
        return {
            "tooltip": translate(_("State"), context=self.request),
            "id": "workflow",
            "icon": "plone-lock",
            "url": self.context.absolute_url() + "/@@fc-workflow",
            "form": {
                "title": translate(
                    _("Change workflow of selected items"), context=self.request
                ),
                "template": self.template(),
                "dataUrl": self.context.absolute_url() + "/@@fc-workflow",
            },
        }


class WorkflowActionView(ContentsBaseAction):
    required_obj_permission = "Modify portal content"
    success_msg = _("Successfully modified items")
    failure_msg = _("Failed to modify items")

    def __call__(self):
        self.pworkflow = getToolByName(self.context, "portal_workflow")
        self.transition_id = self.request.form.get("transition", None)
        self.comments = self.request.form.get("comments", "")
        self.recurse = self.request.form.get("recurse", "no") == "yes"
        if self.request.form.get("render") == "yes":
            # asking for render information
            selection = self.get_selection()
            catalog = getToolByName(self.context, "portal_catalog")
            brains = catalog(UID=selection, show_inactive=True)
            transitions = []
            for brain in brains:
                obj = brain.getObject()
                for transition in self.pworkflow.getTransitionsFor(obj):
                    tdata = {
                        "id": transition["id"],
                        "title": self.context.translate(safe_text(transition["name"])),
                    }
                    if tdata not in transitions:
                        transitions.append(tdata)
            return self.json({"transitions": transitions})
        return super().__call__()

    def action(self, obj, bypass_recurse=False):
        transitions = self.pworkflow.getTransitionsFor(obj)
        if self.transition_id in [t["id"] for t in transitions]:
            try:
                # set effective date if not already set
                if obj.EffectiveDate() == "None":
                    obj.setEffectiveDate(DateTime())

                self.pworkflow.doActionFor(
                    obj, self.transition_id, comment=self.comments
                )
                if check_default_page_via_view(obj, self.request):
                    self.action(obj.aq_parent, bypass_recurse=True)
                recurse = self.recurse and not bypass_recurse
                if recurse and IFolderish.providedBy(obj):
                    for sub in obj.values():
                        self.action(sub)
                obj.reindexObject()
            except ConflictError:
                raise
            except Exception:
                self.errors.append(
                    _(
                        "Could not transition: ${title}",
                        mapping={"title": self.objectTitle(obj)},
                    )
                )
