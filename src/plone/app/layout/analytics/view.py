from plone.base.interfaces import ISiteSchema
from plone.registry.interfaces import IRegistry
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet


UNWANTED_TAGS = ["base", "title"]


@implementer(IViewlet)
class AnalyticsViewlet(BrowserView):
    render = ViewPageTemplateFile("view.pt")
    record_name = "webstats_js"

    def __init__(self, context, request, view, manager):
        super().__init__(context, request)
        self.__parent__ = view
        self.view = view
        self.manager = manager

    @property
    def webstats_js(self):
        registry = getUtility(IRegistry)
        site_settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        return getattr(site_settings, self.record_name, "")

    def update(self):
        """The viewlet manager _updateViewlets requires this method"""
        pass


@implementer(IViewlet)
class AnalyticsHeadViewlet(AnalyticsViewlet):
    render = ViewPageTemplateFile("view_head.pt")
    record_name = "webstats_head_js"
