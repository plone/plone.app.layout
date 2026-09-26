from Products.CMFEditions.browser.views import VersionsHistoryForm as ApiVersionsHistoryForm
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

import os


class VersionsHistoryForm(ApiVersionsHistoryForm):
    template = ViewPageTemplateFile("templates/versions_history_form.pt")


css_path = os.path.join(os.path.dirname(__file__), "compare.css")
with open(css_path) as myfile:
    COMPARE_CSS = myfile.read()


class CompareCSS(BrowserView):
    """Formerly skins/CMFEditions/compare.css.dtml

    Should be a browser resource, but I don't want to change plone.app.iterate just now.
    That will further complicate an already complex PR.
    """

    def __call__(self):
        return COMPARE_CSS
