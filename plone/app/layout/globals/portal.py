from .interfaces import IPortalState
from Acquisition import aq_inner
from plone.base.interfaces import IPloneSiteRoot
from plone.base.interfaces import ISearchSchema
from plone.base.interfaces import ISiteSchema
from plone.base.navigationroot import get_navigation_root
from plone.base.navigationroot import get_navigation_root_object
from plone.i18n.interfaces import ILanguageSchema
from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless
from plone.registry.interfaces import IRegistry
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from zope.component import getUtility
from zope.component import providedBy
from zope.component.hooks import getSite
from zope.interface import implementer


RIGHT_TO_LEFT = ["ar", "fa", "he", "ps"]


@implementer(IPortalState)
class PortalState(BrowserView):
    """Information about the state of the portal"""

    @memoize_contextless
    def portal(self):
        closest_site = getSite()
        if closest_site is not None:
            for potential_portal in closest_site.aq_chain:
                if ISiteRoot in providedBy(potential_portal):
                    return potential_portal
        return None

    @memoize_contextless
    def portal_title(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        return settings.site_title

    @memoize_contextless
    def portal_url(self):
        return self.portal().absolute_url()

    @memoize
    def navigation_root(self):
        context = aq_inner(self.context)
        portal = self.portal()
        return get_navigation_root_object(context, portal)

    @memoize
    def navigation_root_title(self):
        navigation_root = self.navigation_root()
        if IPloneSiteRoot.providedBy(navigation_root):
            return self.portal_title()

        title = self.navigation_root().Title
        if callable(title):
            return title()
        else:
            return title

    @memoize
    def navigation_root_path(self):
        return get_navigation_root(aq_inner(self.context))

    @memoize
    def navigation_root_url(self):
        rootPath = self.navigation_root_path()
        return self.request.physicalPathToURL(rootPath)

    @memoize_contextless
    def default_language(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ILanguageSchema, prefix="plone")
        return settings.default_language

    def language(self):
        return (
            self.request.get("LANGUAGE", None)
            or aq_inner(self.context).Language()
            or self.default_language()
        )

    def locale(self):
        return self.request.locale

    def is_rtl(self):
        language = self.language()
        if not language:
            return False
        if language[:2] in RIGHT_TO_LEFT:
            return True
        return False

    @memoize_contextless
    def member(self):
        context = aq_inner(self.context)
        tool = getToolByName(context, "portal_membership")
        return tool.getAuthenticatedMember()

    @memoize_contextless
    def anonymous(self):
        context = aq_inner(self.context)
        tool = getToolByName(context, "portal_membership")
        return bool(tool.isAnonymousUser())

    @memoize_contextless
    def friendly_types(self):
        context = aq_inner(self.context)
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISearchSchema, prefix="plone")
        not_searched = settings.types_not_searched

        types = getToolByName(context, "portal_types").listContentTypes()
        return [t for t in types if t not in not_searched]
