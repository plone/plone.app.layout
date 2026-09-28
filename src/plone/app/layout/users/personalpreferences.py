from plone.app.layout.users.account import AccountPanelForm
from plone.app.users.browser.personalpreferences import IPersonalPreferences
from plone.base import PloneMessageFactory as _
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class PersonalPreferencesPanel(AccountPanelForm):
    """Implementation of personalize form that uses z3c.form."""

    form_name = _("legend_personal_details", "Personal Details")
    schema = IPersonalPreferences

    @property
    def description(self):
        userid = self.request.form.get("userid")
        mt = getToolByName(self.context, "portal_membership")
        if userid and (userid != mt.getAuthenticatedMember().getId()):
            # editing someone else's profile
            return _(
                "description_preferences_form_otheruser",
                default="Personal settings for $name",
                mapping={"name": userid},
            )
        else:
            # editing my own profile
            return _("description_my_preferences", default="Your personal settings.")

    def updateWidgets(self):
        super().updateWidgets()

        self.widgets["language"].noValueMessage = _(
            "vocabulary-missing-single-value-for-edit",
            "Language neutral (site default)",
        )
        self.widgets["wysiwyg_editor"].noValueMessage = _(
            "vocabulary-available-editor-novalue", "Use site default"
        )

    def __call__(self):
        self.request.set("disable_border", 1)
        return super().__call__()


class PersonalPreferencesConfiglet(PersonalPreferencesPanel):
    """Control panel version of the personal preferences panel"""

    template = ViewPageTemplateFile("account-configlet.pt")
    tab = "userprefs"
