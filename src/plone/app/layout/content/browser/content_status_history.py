from Acquisition import aq_parent
from plone.base import PloneMessageFactory as _
from plone.base.defaultpage import is_default_page
from plone.base.utils import human_readable_size
from plone.base.utils import is_expired
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import field
from z3c.form import form
from zope.deprecation.deprecation import deprecate
from zope.interface import Interface
from zope.publisher.browser import BrowserView
from zope.schema import Datetime
from zope.schema.fieldproperty import FieldProperty


class IContentStatusHistoryDates(Interface):
    """Interface for the two dates on content status history view"""

    effective_date = Datetime(
        title=_("label_effective_date", default="Publishing Date"),
        description=_(
            "help_effective_date_content_status_history",
            default="The date when the item will be published. If no "
            "date is selected the item will be published immediately.",
        ),
        required=False,
    )

    expiration_date = Datetime(
        title=_("label_expiration_date", default="Expiration Date"),
        description=_(
            "help_expiration_date_content_status_history",
            default="The date when the item expires. This will automatically "
            "make the item invisible for others at the given date. "
            "If no date is chosen, it will never expire.",
        ),
        required=False,
    )


class ContentStatusHistoryDatesForm(form.Form):
    fields = field.Fields(IContentStatusHistoryDates)
    ignoreContext = True
    label = "Content status history dates"

    effective_date = FieldProperty(IContentStatusHistoryDates["effective_date"])
    expiration_date = FieldProperty(IContentStatusHistoryDates["expiration_date"])


class ContentStatusHistoryView(BrowserView):
    template = ViewPageTemplateFile("templates/content_status_history.pt")

    def __init__(self, context, request):
        super().__init__(context, request)

        self.dates_form = ContentStatusHistoryDatesForm(context, request)
        self.dates_form.updateWidgets()
        self.errors = {}

    def __call__(
        self,
        workflow_action=None,
        paths=[],
        comment="",
        effective_date=None,
        expiration_date=None,
        include_children=False,
        *args,
    ):
        data = self.dates_form.extractData()
        if self.request.get("form.widgets.effective_date-calendar", None) and data:
            effective_date = data[0]["effective_date"].strftime("%Y-%m-%d %H:%M")

        if self.request.get("form.widgets.expiration_date-calendar", None) and data:
            expiration_date = data[0]["expiration_date"].strftime("%Y-%m-%d %H:%M")

        if self.request.get("form.button.Cancel", None):
            return self.request.RESPONSE.redirect(
                "%s/view" % self.context.absolute_url()
            )

        if self.request.get("form.submitted", None):
            self.validate(workflow_action=workflow_action, paths=paths)
            if self.errors:
                IStatusMessage(self.request).add(
                    _("Please correct the indicated errors."), type="error"
                )
                return self.template()

        if self.request.get("form.button.Publish", None):
            return self.context.restrictedTraverse("content_status_modify")(
                workflow_action=workflow_action,
                comment=comment,
                effective_date=effective_date,
                expiration_date=expiration_date,
            )

        if self.request.get("form.button.FolderPublish", None):
            self.context.restrictedTraverse("folder_publish")(
                workflow_action=workflow_action,
                paths=paths,
                comment=comment,
                expiration_date=expiration_date,
                effective_date=effective_date,
                include_children=include_children,
            )

        return self.template()

    def validate(self, workflow_action=None, paths=[]):
        if workflow_action is None:
            self.errors["workflow_action"] = _("You must select a publishing action.")

        if not paths:
            self.errors["paths"] = _("You must select content to change.")
            # If there are no paths, it's mostly a mistake
            # Set paths using orgi_paths, otherwise users are getting confused
            orig_paths = self.request.get("orig_paths")
            self.request.set("paths", orig_paths)

    def get_objects_from_path_list(self, paths=[]):
        contents = []
        portal = getToolByName(self.context, "portal_url").getPortalObject()
        for path in paths:
            obj = portal.restrictedTraverse(str(path), None)
            if obj is not None:
                contents.append(obj)
        return contents

    def redirect_to_referrer(self):
        referer = self.request.get("HTTP_REFERER", "")
        target_url = referer.split("?", 1)[0]
        return self.request.RESPONSE.redirect(target_url)

    def isExpired(self, content):
        return is_expired(content)

    def is_default_page(self, obj):
        return is_default_page(aq_parent(self.context), obj)

    @deprecate(
        "This method is deprecated since Plone 6, "
        "use the @@plone/human_readable_size method instead"
    )
    def human_readable_size(self, size):
        return human_readable_size(size)
