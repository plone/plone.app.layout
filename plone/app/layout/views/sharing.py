from plone.app.layout import _
from plone.app.workflow.browser.sharing import SharingView as ApiSharingView
from plone.app.workflow.events import LocalrolesModifiedEvent
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from zExceptions import Forbidden
from zope.event import notify


class SharingView(ApiSharingView):
    # Actions
    template = ViewPageTemplateFile("sharing.pt")

    def __call__(self):
        """Perform the update and redirect if necessary, or render the page"""
        postback = self.handle_form()
        if postback:
            return self.template()
        else:
            context_state = self.context.restrictedTraverse("@@plone_context_state")
            url = context_state.view_url()
            self.request.response.redirect(url)

    def handle_form(self):
        """
        We split this out so we can reuse this for ajax.
        Will return a boolean if it was a post or not
        """
        postback = True

        form = self.request.form
        submitted = form.get("form.submitted", False)
        save_button = form.get("form.button.Save", None) is not None
        cancel_button = form.get("form.button.Cancel", None) is not None
        if submitted and save_button and not cancel_button:
            if not self.request.get("REQUEST_METHOD", "GET") == "POST":
                raise Forbidden

            authenticator = self.context.restrictedTraverse("@@authenticator", None)
            if not authenticator.verify():
                raise Forbidden

            # Update the acquire-roles setting
            if self.can_edit_inherit():
                inherit = bool(form.get("inherit", False))
                reindex = self.update_inherit(inherit, reindex=False)
            else:
                reindex = False

            # Update settings for users and groups
            entries = form.get("entries", [])
            roles = [r["id"] for r in self.roles()]
            settings = []
            for entry in entries:
                settings.append(
                    dict(
                        id=entry["id"],
                        type=entry["type"],
                        roles=[r for r in roles if entry.get("role_%s" % r, False)],
                    )
                )
            if settings:
                reindex = self.update_role_settings(settings, reindex=False) or reindex
            if reindex:
                self.context.reindexObjectSecurity()
                notify(LocalrolesModifiedEvent(self.context, self.request))
            IStatusMessage(self.request).addStatusMessage(
                _("Changes saved."), type="info"
            )

        # Other buttons return to the sharing page
        if cancel_button:
            postback = False

        return postback
