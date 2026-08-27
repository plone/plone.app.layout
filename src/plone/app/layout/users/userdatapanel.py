from plone.app.layout.users.account import AccountPanelForm
from plone.app.users.browser.userdatapanel import getUserDataSchema
from plone.base import PloneMessageFactory as _
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zExceptions import NotFound

try:
    from html import escape
except ImportError:
    from cgi import escape


class UserDataPanel(AccountPanelForm):
    form_name = _("User Data Form")
    enableCSRFProtection = True

    @property
    def schema(self):
        schema = getUserDataSchema()
        return schema

    @property
    def description(self):
        userid = self.request.form.get("userid")
        mt = getToolByName(self.context, "portal_membership")
        if userid and (userid != mt.getAuthenticatedMember().getId()):
            # editing someone else's profile
            return _(
                "description_personal_information_form_otheruser",
                default="Change personal information for $name",
                mapping={"name": escape(userid)},
            )
        else:
            # editing my own profile
            return _(
                "description_personal_information_form",
                default="Change your personal information",
            )

    def __call__(self):
        userid = self.request.form.get("userid")
        if userid:
            mt = getToolByName(self.context, "portal_membership")
            if mt.getMemberById(userid) is None:
                raise NotFound("User does not exist.")
        self.request.set("disable_border", 1)
        return super().__call__()


class UserDataConfiglet(UserDataPanel):
    """Control panel version of the userdata panel"""

    template = ViewPageTemplateFile("account-configlet.pt")
    tab = "userdata"
