from BTrees.OOBTree import OOBTree
from gzip import GzipFile
from io import BytesIO
from plone.base.batch import Batch
from plone.base.interfaces import IPloneSiteRoot
from plone.base.interfaces import ISiteSchema
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.interfaces import NotFound

import math


def _render_cachekey(fun, self):
    # Cache by filename
    mtool = getToolByName(self.context, "portal_membership")
    if not mtool.isAnonymousUser():
        raise ram.DontCache

    url = self.context.absolute_url()
    catalog = getToolByName(self.context, "portal_catalog")
    counter = catalog.getCounter()
    return f"{url}/{self.filename}/{counter}"


class SiteMapView(BrowserView):
    """Creates the sitemap as explained in the specifications.

    http://www.sitemaps.org/protocol.php
    """

    template_index = ViewPageTemplateFile("sitemap-index.xml")
    template = ViewPageTemplateFile("sitemap.xml")
    BATCH_SIZE = 5000

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.filename = "sitemap.xml.gz"

    def _objects(self):
        """Returns the data to create the sitemap."""
        catalog = getToolByName(self.context, "portal_catalog")
        query = {}
        utils = getToolByName(self.context, "plone_utils")
        query["portal_type"] = utils.getUserFriendlyTypes()
        registry = getUtility(IRegistry)
        typesUseViewActionInListings = frozenset(
            registry.get("plone.types_use_view_action_in_listings", [])
        )

        is_plone_site_root = IPloneSiteRoot.providedBy(self.context)
        if not is_plone_site_root:
            query["path"] = "/".join(self.context.getPhysicalPath())

        query["is_default_page"] = True
        default_page_modified = OOBTree()

        for item in catalog.searchResults(query):
            key = item.getURL().rsplit("/", 1)[0]
            value = (item.modified.micros(), item.modified.ISO8601())
            default_page_modified[key] = value

        # The plone site root is not catalogued.
        if is_plone_site_root:
            loc = self.context.absolute_url()
            date = self.context.modified()
            # Comparison must be on GMT value
            modified = (date.micros(), date.ISO8601())
            default_modified = default_page_modified.get(loc, None)
            if default_modified is not None:
                modified = max(modified, default_modified)
            lastmod = modified[1]
            yield {
                "loc": loc,
                "lastmod": lastmod,
                # 'changefreq': 'always',
                #  hourly/daily/weekly/monthly/yearly/never
                # 'prioriy': 0.5, # 0.0 to 1.0
            }

        query["is_default_page"] = False
        for item in catalog.searchResults(query):
            loc = item.getURL()
            date = item.modified
            # Comparison must be on GMT value
            modified = (date.micros(), date.ISO8601())
            default_modified = default_page_modified.get(loc, None)
            if default_modified is not None:
                modified = max(modified, default_modified)
            lastmod = modified[1]
            if item.portal_type in typesUseViewActionInListings:
                loc += "/view"
            yield {
                "loc": loc,
                "lastmod": lastmod,
                # 'changefreq': 'always',
                #  hourly/daily/weekly/monthly/yearly/never
                # 'prioriy': 0.5, # 0.0 to 1.0
            }

    def objects(self):
        items = list(self._objects())
        page = self.request.get("page", "0")
        page_int = int(page)
        import pdb

        pdb.set_trace()
        if page_int:
            b_start = (page_int - 1) * self.BATCH_SIZE
            batch = Batch(items, start=b_start, size=self.BATCH_SIZE)
            return batch

        return []

    def sitemap_count(self):
        items = self._objects()
        if items:
            item_count = len(list(items))
            if item_count:
                count = math.ceil(item_count / self.BATCH_SIZE)
                return range(1, count + 1)

        return []

    @ram.cache(_render_cachekey)
    def generate(self):
        """Generates the Gzipped sitemap."""
        if "page" in self.request:
            xml = self.template()
        else:
            xml = self.template_index()

        fp = BytesIO()
        gzip = GzipFile(self.filename, "wb", 9, fp)
        if isinstance(xml, str):
            xml = xml.encode("utf8")
        gzip.write(xml)
        gzip.close()
        data = fp.getvalue()
        fp.close()
        return data

    def __call__(self):
        """Checks if the sitemap feature is enable and returns it."""
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        if not settings.enable_sitemap:
            raise NotFound(self.context, self.filename, self.request)

        self.request.response.setHeader("Content-Type", "application/octet-stream")
        return self.generate()

    def navroot_url(self):
        pps = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        return pps.navigation_root_url()
