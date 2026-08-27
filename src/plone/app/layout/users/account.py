from plone.app.users.browser.account import AccountPanelValidation
from plone.app.users.browser.interfaces import IAccountPanelForm
from plone.app.users.utils import notifyWidgetActionExecutionError
from plone.autoform.form import AutoExtensibleForm
from plone.base import PloneMessageFactory as _
from plone.protect import CheckAuthenticator
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.controlpanel.events import ConfigurationChangedEvent
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from z3c.form import form
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.component import getMultiAdapter
from zope.event import notify
from zope.interface import implementer
from ZTUtils import make_query


@implementer(IAccountPanelForm)
class AccountPanelForm(AutoExtensibleForm, form.Form, AccountPanelValidation):
    """A simple form to be used as a basis for account panel screens."""

    schema = IAccountPanelForm
    template = ViewPageTemplateFile("account-panel.pt")
    enableCSRFProtection = True

    hidden_widgets = []
    successMessage = _("Changes saved.")
    noChangesMessage = _("No changes made.")

    @lazy_property
    def member(self):
        mtool = getToolByName(self.context, "portal_membership")
        if self.request.get("userid"):
            return mtool.getMemberById(self.request.get("userid"))

    @property
    def label(self):
        return self.member.getProperty("fullname") or self.member.getUserName()

    def _differentEmail(self, email):
        """Check if the submitted form email address differs from the existing
        one.

        Keeping your email the same (which happens when you change something
        else on the personalize form) or changing it back to your login name,
        is fine.

        So: we only return True if it is *really* a different email.
        """
        member = self.member
        if email in (member.getId(), member.getUserName()):
            return False
        # By default, PAS transforms login names to lowercase, at least when
        # email-as-login is used.  So compare the transformed/normalized names.
        pas = getToolByName(self.context, "acl_users")
        email_normalized = pas.applyTransform(email)
        # The user name should already have been normalized, but let's make sure.
        login_normalized = pas.applyTransform(member.getUserName())
        return email_normalized != login_normalized

    def makeQuery(self):
        userid = self.request.form.get("userid", None)
        if userid is not None:
            return "?{}".format(make_query({"userid": userid}))
        return ""

    def action(self):
        return self.request.getURL() + self.makeQuery()

    def validate_email(self, action, data):
        error_keys = [error.field.getName() for error in action.form.widgets.errors]
        if "email" in error_keys:
            # There is already a validation error for email,
            # so there is no need for further validation.
            return
        err_str = super().validate_email(data)
        if err_str:
            notifyWidgetActionExecutionError(action, "email", err_str)

    def validate_portrait(self, action, data):
        """Portrait validation.
        Checks if image is supported by Pillow.
        SVG files are not yet supported.
        """
        error_keys = [error.field.getName() for error in action.form.widgets.errors]
        if "portrait" in error_keys:
            return
        err_str = super().validate_portrait(data)
        if err_str:
            notifyWidgetActionExecutionError(action, "portrait", err_str)

    @button.buttonAndHandler(_("Save"))
    def handleSave(self, action):
        CheckAuthenticator(self.request)
        data, errors = self.extractData()

        # Extra validation for email, when it is there.  email is not in the
        # data when you are at the personal-preferences page.
        if "email" in data:
            self.validate_email(action, data)

        # Validate portrait, upload image could be not supported
        # by PIL what raises an exception when scaling image.
        if "portrait" in data:
            self.validate_portrait(action, data)

        if action.form.widgets.errors:
            self.status = self.formErrorsMessage
            return
        if self.applyChanges(data):
            IStatusMessage(self.request).addStatusMessage(
                self.successMessage, type="info"
            )
            notify(ConfigurationChangedEvent(self, data))
            self._on_save(data)
        else:
            IStatusMessage(self.request).addStatusMessage(
                self.noChangesMessage, type="info"
            )
        self.request.response.redirect(self.action())

    def updateActions(self):
        super().updateActions()
        if self.actions and "save" in self.actions:
            self.actions["save"].addClass("btn btn-primary")

    @button.buttonAndHandler(_("Cancel"))
    def cancel(self, action):
        IStatusMessage(self.request).addStatusMessage(
            _("Changes canceled."), type="info"
        )
        self.request.response.redirect(
            "{}{}".format(self.request["ACTUAL_URL"], self.makeQuery())
        )

    def _on_save(self, data=None):
        pass

    def prepareObjectTabs(self, default_tab="view", sort_first=["folderContents"]):
        context = self.context
        mt = getToolByName(context, "portal_membership")
        tabs = []
        navigation_root_url = context.absolute_url()

        def _check_allowed(context, request, name):
            """Check, if user has required permissions on view."""
            view = getMultiAdapter((context, request), name=name)
            allowed = True
            for perm in view.__ac_permissions__:
                allowed = allowed and mt.checkPermission(perm[0], context)
            return allowed

        if _check_allowed(context, self.request, "personal-information"):
            tabs.append(
                {
                    "title": _(
                        "title_personal_information_form", "Personal Information"
                    ),
                    "url": navigation_root_url + "/@@personal-information",
                    "selected": (self.__name__ == "personal-information"),
                    "id": "user_data-personal-information",
                }
            )

        if _check_allowed(context, self.request, "personal-preferences"):
            tabs.append(
                {
                    "title": _("Personal Preferences"),
                    "url": navigation_root_url + "/@@personal-preferences",
                    "selected": (self.__name__ == "personal-preferences"),
                    "id": "user_data-personal-preferences",
                }
            )

        member = mt.getAuthenticatedMember()
        if member.canPasswordSet():
            tabs.append(
                {
                    "title": _("label_password", "Password"),
                    "url": navigation_root_url + "/@@change-password",
                    "selected": (self.__name__ == "change-password"),
                    "id": "user_data-change-password",
                }
            )
        return tabs
