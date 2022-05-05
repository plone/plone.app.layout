from plone.app.layout.viewlets.common import PersonalBarViewlet
from plone.app.viewletmanager.manager import OrderedViewletManager
from plone.memoize.instance import memoize
from plone.registry.interfaces import IRegistry
from plone.base.interfaces.controlpanel import ISiteSchema
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.component import getUtility


class ToolbarViewletManager(OrderedViewletManager):
    custom_template = ViewPageTemplateFile("toolbar.pt")

    @property
    @memoize
    def _settings(self):
        registry = getUtility(IRegistry)
        return registry.forInterface(ISiteSchema, prefix="plone", check=False)

    def base_render(self):
        return super().render()

    def render(self):
        return self.custom_template()

    @property
    @memoize
    def context_state(self):
        return getMultiAdapter((self.context, self.request), name="plone_context_state")

    @property
    @memoize
    def portal_state(self):
        return getMultiAdapter((self.context, self.request), name="plone_portal_state")

    def toolbar_position(self):
        return self._settings.toolbar_position

    def get_personal_bar(self):
        viewlet = PersonalBarViewlet(self.context, self.request, self.__parent__, self)
        viewlet.update()
        return viewlet

    def get_toolbar_logo(self):
        portal_url = self.portal_state.portal_url()
        try:
            logo = self._settings.toolbar_logo
        except AttributeError:
            logo = "/++plone++static/plone-toolbarlogo.svg"
        if not logo:
            logo = "/++plone++static/plone-toolbarlogo.svg"
        return portal_url + logo

    def show_switcher(self):
        return False
