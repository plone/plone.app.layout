from Acquisition import aq_inner
from plone.base import PloneMessageFactory as _
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getMultiAdapter
from zope.component import getUtility


class DefaultViewSelectionView(BrowserView):
    def isValidTemplate(self, templateId):
        return templateId in [a[0] for a in self.vocab]

    def canSelectDefaultPage(self):
        return self.context.isPrincipiaFolderish and self.context.canSetDefaultPage()

    @property
    def vocab(self):
        return self.context.getAvailableLayouts()

    @property
    def selectedLayout(self):
        if not self.context_state.is_default_page():
            return self.context.getLayout()
        return ""

    def selectViewTemplate(self):
        templateId = self.request.get("templateId")

        if self.isValidTemplate(templateId):
            self.context.setLayout(templateId)

        self.request.response.redirect(self.context.absolute_url() + "/view")

    @property
    def action_url(self):
        return f"{self.context_state.object_url():s}/select_default_view"

    def __call__(self):
        self.context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )

        template_id = self.request.form.get("templateId")
        context_view_url = self.context_state.object_url() + "/view"

        if self.request.form.get("form.button.Cancel"):
            self.request.response.redirect(context_view_url)

        if self.request.form.get("form.button.Save") and not template_id:
            IStatusMessage(self.request).add(
                "Please select a template.", type="warning"
            )

        if self.request.form.get("form.button.Save") and template_id:
            # Make sure this is a valid template
            if not self.isValidTemplate(template_id):
                IStatusMessage(self.request).add("Invalid view.", type="error")
                return self.index()
            # Update the template
            self.context.setLayout(template_id)
            IStatusMessage(self.request).add("View changed.")
            # Redirect to context view
            self.request.response.redirect(context_view_url)

        return self.index()


class DefaultPageSelectionView(BrowserView):
    def __call__(self):
        if "form.buttons.Save" in self.request.form:
            if "objectId" not in self.request.form:
                message = _("Please select an item to use.")
                msgtype = "error"
            else:
                objectId = self.request.form["objectId"]

                if objectId not in self.context.objectIds():
                    message = _(
                        "There is no object with short name ${name} " "in this folder.",
                        mapping={"name": objectId},
                    )
                    msgtype = "error"
                else:
                    self.context.setDefaultPage(objectId)
                    message = _("View changed.")
                    msgtype = "info"
                    self.request.response.redirect(self.context.absolute_url())
            IStatusMessage(self.request).add(message, msgtype)
        elif "form.buttons.Cancel" in self.request.form:
            self.request.response.redirect(self.context.absolute_url())

        return self.index()

    def get_selectable_items(self):
        """Return brains in this container that can be used as default_pages"""
        context = aq_inner(self.context)
        registry = getUtility(IRegistry)
        view_types = registry.get("plone.types_use_view_action_in_listings", [])
        default_page_types = registry.get("plone.default_page_types", [])
        portal_types = getToolByName(self.context, "portal_types")
        portal_catalog = getToolByName(self.context, "portal_catalog")

        results = []
        for brain in portal_catalog(
            path={"query": "/".join(context.getPhysicalPath()), "depth": 1},
            sort_on="getObjPositionInParent",
        ):
            portal_type = brain.portal_type
            if portal_type in view_types:
                # Skip files and images
                continue

            if portal_type in default_page_types:
                # Allow types that are explicitly in default_page_types
                results.append(brain)
                continue

            if brain.is_folderish:
                fti = portal_types.get(portal_type)
                if not fti:
                    continue
                if (
                    fti.filter_content_types
                    and fti.allowed_content_types
                    or not fti.filter_content_types
                ):
                    # Disallow folderish types if you can't add any content.
                    # To override you have to add type to default_page_types
                    continue

                results.append(brain)
        return results
