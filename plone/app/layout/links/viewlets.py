from Acquisition import aq_inner
from plone.app.layout.viewlets import ViewletBase
from plone.app.uuid.utils import uuidToObject
from plone.base.interfaces import ISiteSyndicationSettings
from plone.base.interfaces.syndication import IFeedSettings
from plone.base.utils import safe_bytes
from plone.formwidget.namedfile.converter import b64decode_file
from plone.memoize import ram
from plone.memoize import view
from plone.memoize.compress import xhtml_compress
from plone.registry.interfaces import IRegistry
from plone.base.interfaces import ISecuritySchema
from plone.base.interfaces import ISiteSchema
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from typing import NoReturn
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory


def get_language(context, request):
    portal_state = getMultiAdapter((context, request), name="plone_portal_state")
    return portal_state.language()


def render_cachekey(fun, self):
    # Include the name of the viewlet as the underlying cache key only
    # takes the module and function name into account, but not the class
    return "\n".join(
        [
            self.__name__,
            self.site_url,
            get_language(aq_inner(self.context), self.request),
        ]
    )


class FaviconViewlet(ViewletBase):

    _template = ViewPageTemplateFile("favicon.pt")
    mimetype: str
    favicon_path: str

    def init_favicon(self) -> NoReturn:
        registry = getUtility(IRegistry)
        settings: ISiteSchema = registry.forInterface(ISiteSchema, prefix="plone")
        self.mimetype: str = getattr(
            settings, "site_favicon_mimetype", "image/vnd.microsoft.icon"
        )
        cachebust = ""
        if getattr(settings, "site_favicon", False):
            # The user has customized the favicon via the Site configlet.
            filename = b64decode_file(settings.site_favicon)[0]

            cachebust = "?name=" + filename
        # The filename is *always* /favicon.ico, irrespective of the content type,
        # because:
        #
        # 1. Browsers obey the content type over the extension.
        # 2. The actual serving view URL for the favicon is always /favicon.ico,
        #    and this name cannot be overridden from here into the view registered
        #    on CMFPlone, where the *actual* serving of the data takes place.
        # 3. Even if we could somehow override the view, there is no easy way to
        #    register in CMFPlone a different browser view for every icon file
        #    name the user may decide to upload.
        # 4. In many cases client applications just hit /favicon.ico irrespective
        #    of what the HTML says (remember that this specific view is only
        #    responsible for generating the metadata that lets the browser know
        #    where to find the favicon URL).
        #
        # However, to allow for users to change their favicons *and* bust their
        # proxy caches, we do use the favicon filename in the served favicon
        # URL.  This does not cover the case of RSS and podcast apps that access
        # /favicon.ico by custom instead of consulting the HTML, but at least
        # it covers pretty much every browser out there.
        self.favicon_path: str = f"{self.navigation_root_url}/favicon.ico{cachebust}"

    def render(self) -> ViewPageTemplateFile:
        self.init_favicon()
        return xhtml_compress(self._template())


class SearchViewlet(ViewletBase):

    _template = ViewPageTemplateFile("search.pt")

    @ram.cache(render_cachekey)
    def render(self):
        return xhtml_compress(self._template())


class AuthorViewlet(ViewletBase):

    _template = ViewPageTemplateFile("author.pt")

    def update(self):
        super().update()
        self.tools = getMultiAdapter((self.context, self.request), name="plone_tools")

    def show(self):
        anonymous = self.portal_state.anonymous()
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISecuritySchema,
            prefix="plone",
        )
        return not anonymous or settings.allow_anon_views_about

    def render(self):
        if self.show():
            return self._template()
        return ""


class RSSViewlet(ViewletBase):
    def getRssLinks(self, obj):
        settings = IFeedSettings(obj, None)
        if settings is None:
            return []
        factory = getUtility(
            IVocabularyFactory, "plone.app.vocabularies.SyndicationFeedTypes"
        )
        vocabulary = factory(self.context)
        urls = []
        for typ in settings.feed_types:
            try:
                term = vocabulary.getTerm(typ)
            except LookupError:
                continue

            urls.append(
                {
                    "title": f"{obj.Title()} - {safe_bytes(term.title)}",
                    "url": obj.absolute_url() + "/" + term.value,
                }
            )
        return urls

    def update(self):
        super().update()
        self.rsslinks = []
        portal = self.portal_state.portal()
        util = getMultiAdapter((self.context, self.request), name="syndication-util")
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        if context_state.is_portal_root():
            if util.site_enabled():
                registry = getUtility(IRegistry)
                try:
                    settings = registry.forInterface(ISiteSyndicationSettings)
                except KeyError:
                    return
                if settings.site_rss_items:
                    for uid in settings.site_rss_items:
                        if not uid:
                            continue
                        obj = uuidToObject(uid)
                        if obj is None and uid[0] == "/":
                            obj = portal.restrictedTraverse(uid.lstrip("/"), None)
                        if obj is not None:
                            self.rsslinks.extend(self.getRssLinks(obj))
                self.rsslinks.extend(self.getRssLinks(portal))
        else:
            if util.context_enabled():
                self.rsslinks.extend(self.getRssLinks(self.context))

    index = ViewPageTemplateFile("rsslink.pt")


class CanonicalURL(ViewletBase):
    """Defines a canonical link relation viewlet to be displayed across the
    site. A canonical page is the preferred version of a set of pages with
    highly similar content. For more information, see:
    https://tools.ietf.org/html/rfc6596
    https://support.google.com/webmasters/answer/139394?hl=en
    """

    @view.memoize
    def render(self):
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        canonical_url = context_state.canonical_object_url()
        return '    <link rel="canonical" href="%s" />' % canonical_url
