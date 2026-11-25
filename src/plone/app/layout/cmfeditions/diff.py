from Products.CMFEditions.browser.diff import DiffView as ApiDiffView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class DiffView(ApiDiffView):
    template = ViewPageTemplateFile("templates/diff.pt")
