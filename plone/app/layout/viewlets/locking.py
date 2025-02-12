from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet


@implementer(IViewlet)
class LockInfoViewlet(BrowserView):
    template = ViewPageTemplateFile("locking.pt")

    def __init__(self, context, request, view, manager):
        super().__init__(context, request)
        self.__parent__ = view
        self.context = context
        self.request = request
        self.view = view
        self.manager = manager
        self.info = getMultiAdapter((context, request), name="plone_lock_info")

    def update(self):
        pass

    def render(self):
        return self.template()

    def lock_is_stealable(self):
        return self.info.lock_is_stealable()

    def lock_info(self):
        return self.info.lock_info()
