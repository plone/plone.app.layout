from zope.interface import implements
from zope.viewlet.interfaces import IViewlet

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class AnalyticsViewlet(BrowserView):
    implements(IViewlet)

    render = ViewPageTemplateFile("view.pt")

    def __init__(self, context, request, view, manager):
        super(AnalyticsViewlet, self).__init__(context, request)
        self.__parent__ = view
        self.context = context
        self.request = request
        self.view = view
        self.manager = manager
        self.webstats_js = ''

    def update(self):
        """render the webstats snippet"""
        ptool = getToolByName(self.context, "portal_properties")
        self.webstats_js = safe_unicode(ptool.site_properties.webstats_js)
