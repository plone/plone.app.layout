from plone.base.interfaces import ISiteSchema
from plone.registry.interfaces import IRegistry
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet
from lxml import html as lxmlhtml


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
        stats = getattr(site_settings, self.record_name, "")
        if stats != "":
            html = lxmlhtml.fromstring(stats)
            if html.xpath("//script"):
                script_tags = [lxmlhtml.tostring(tag, encoding='unicode') for tag in html.xpath("//script")]
                return "\n".join(script_tags)
        return ""

    def update(self):
        """The viewlet manager _updateViewlets requires this method"""
        pass


@implementer(IViewlet)
class AnalyticsHeadViewlet(AnalyticsViewlet):
    render = ViewPageTemplateFile("view_head.pt")
    record_name = "webstats_head_js"
