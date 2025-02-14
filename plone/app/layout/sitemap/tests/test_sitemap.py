from DateTime import DateTime
from gzip import GzipFile
from io import BytesIO
from plone.app.layout.testing import INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.base.interfaces import INavigationRoot
from plone.base.interfaces import ISearchSchema
from plone.base.interfaces import ISiteSchema
from plone.base.utils import safe_text
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.publisher.interfaces import INotFound

import unittest


class SiteMapTestCase(unittest.TestCase):
    """base test case with convenience methods for all sitemap tests"""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        registry = getUtility(IRegistry)
        self.site_settings = registry.forInterface(ISiteSchema, prefix="plone")
        self.site_settings.enable_sitemap = True
        self.sitemap = getMultiAdapter(
            (self.portal, self.portal.REQUEST), name="sitemap.xml.gz"
        )
        self.wftool = getToolByName(self.portal, "portal_workflow")

        # we need to explicitly set a workflow cause we can't rely on the
        # test environment.
        # `instance test -m plone.app.layout`:
        # wftool._default_chain == 'simple_publication_workflow'
        # `instance test -m plone.app`:
        # wftool._default_chain == 'plone_workflow'
        self.wftool.setChainForPortalTypes(["Document"], "simple_publication_workflow")

        # setup private content that isn't accessible for anonymous
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory(id="private", type_name="Document")
        private = self.portal.private
        self.assertTrue("private" == self.wftool.getInfoFor(private, "review_state"))

        # setup published content that is accessible for anonymous
        self.portal.invokeFactory(id="published", type_name="Document")
        published = self.portal.published
        self.wftool.doActionFor(published, "publish")
        self.assertTrue(
            "published" == self.wftool.getInfoFor(published, "review_state")
        )

        # setup pending content that isn't accessible for anonymous
        self.portal.invokeFactory(id="pending", type_name="Document")
        pending = self.portal.pending
        self.wftool.doActionFor(pending, "submit")
        self.assertTrue("pending" == self.wftool.getInfoFor(pending, "review_state"))
        logout()

    def uncompress(self, sitemapdata):
        sio = BytesIO(sitemapdata)
        unzipped = GzipFile(fileobj=sio)
        xml = unzipped.read()
        unzipped.close()
        return safe_text(xml)

    def test_disabled(self):
        """
        If the sitemap is disabled throws a 404 error.
        """
        self.site_settings.enable_sitemap = False
        try:
            self.sitemap()
        except Exception as e:
            # zope2 and repoze.zope2 use different publishers and raise
            # different exceptions. but both implement INotFound.
            self.assertTrue(INotFound.providedBy(e))
        else:
            self.fail("The disabled sitemap view has to raise NotFound!")

    def test_authenticated_before_anonymous(self):
        """
        Requests for the sitemap by authenticated users are not cached.
        anomymous users get a uncached sitemap that only contains content
        that they are supposed to see.
        """

        # first round as an authenticated (manager)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertTrue("<loc>http://nohost/plone/private</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/pending</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/published</loc>" in xml)

        # second round as anonymous
        logout()
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/private</loc>" in xml)
        self.assertFalse("<loc>http://nohost/plone/pending</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/published</loc>" in xml)

    def test_anonymous_before_authenticated(self):
        """
        Requests for the sitemap by anonymous users are cached.
        authenticated users get a uncached sitemap. Test that the cached
        Sitemap is not delivered to authenticated users.
        """

        # first round as anonymous
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/private</loc>" in xml)
        self.assertFalse("<loc>http://nohost/plone/pending</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/published</loc>" in xml)

        # second round as an authenticated (manager)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertTrue("<loc>http://nohost/plone/private</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/pending</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/published</loc>" in xml)

    def test_changed_catalog(self):
        """
        The sitemap is generated from the catalog. If the catalog changes, a
        new sitemap has to be generated.
        """
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/pending</loc>" in xml)

        # changing the workflow state
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        pending = self.portal.pending
        self.wftool.doActionFor(pending, "publish")
        logout()

        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertTrue("<loc>http://nohost/plone/pending</loc>" in xml)

        # removing content
        login(self.portal, TEST_USER_NAME)
        self.portal.manage_delObjects(
            [
                "published",
            ]
        )
        logout()

        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/published</loc>" in xml)

    def test_navroot(self):
        """
        Sitemap generated from an INavigationRoot
        """
        # setup navroot content that is accessible for anonymous
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.invokeFactory(id="navroot", type_name="Folder")
        navroot = self.portal.navroot
        self.wftool.doActionFor(navroot, "publish")
        self.assertTrue("published" == self.wftool.getInfoFor(navroot, "review_state"))
        alsoProvides(navroot, INavigationRoot)
        navroot.invokeFactory(id="published", type_name="Document")
        published = navroot.published
        self.wftool.doActionFor(published, "publish")
        self.assertTrue(
            "published" == self.wftool.getInfoFor(published, "review_state")
        )
        logout()

        sitemap = getMultiAdapter(
            (self.portal.navroot, self.portal.REQUEST), name="sitemap.xml.gz"
        )
        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(sitemap())
        self.assertFalse("<loc>http://nohost/plone/published</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/navroot</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/navroot/published</loc>" in xml)

    def test_types_not_searched(self):
        """
        Test that types_not_searched is respected
        """
        # Set News Items not to be searchable (more likely Images)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.invokeFactory(id="newsitem", type_name="News Item")
        newsitem = self.portal.newsitem
        self.wftool.doActionFor(newsitem, "publish")
        self.assertTrue("published" == self.wftool.getInfoFor(newsitem, "review_state"))
        registry = getUtility(IRegistry)
        search_settings = registry.forInterface(ISearchSchema, prefix="plone")
        search_settings.types_not_searched = ("News Item",)
        logout()

        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/newsitem</loc>" in xml)

    def test_typesUseViewActionInListings(self):
        """
        Test that typesUseViewActionInListings is respected
        """
        # Set News Items not to be searchable (more likely Images)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.invokeFactory(id="newsitem", type_name="News Item")
        newsitem = self.portal.newsitem
        self.wftool.doActionFor(newsitem, "publish")
        self.assertTrue("published" == self.wftool.getInfoFor(newsitem, "review_state"))
        registry = getUtility(IRegistry)
        registry["plone.types_use_view_action_in_listings"] = ["News Item"]

        logout()

        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertTrue("<loc>http://nohost/plone/newsitem/view</loc>" in xml)

    def test_default_pages(self):
        """
        Default pages should show up at their parent's url with the greater of
        their or their parent's modification time.
        """

        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        self.portal.invokeFactory(id="folder", type_name="Folder")
        folder = self.portal.folder
        folder.default_page = "default"
        self.wftool.doActionFor(folder, "publish")
        self.assertTrue("published" == self.wftool.getInfoFor(folder, "review_state"))

        folder.invokeFactory(id="default", type_name="Document")
        default = folder.default
        self.wftool.doActionFor(default, "publish")
        self.assertTrue("published" == self.wftool.getInfoFor(default, "review_state"))
        self.assertTrue(self.portal.plone_utils.isDefaultPage(default))
        default.modification_date = DateTime("2001-01-01")
        folder.modification_date = DateTime("2000-01-01")
        self.portal.portal_catalog.reindexObject(
            folder, idxs=["modified", "is_default_page", "effective"]
        )
        self.portal.portal_catalog.reindexObject(
            default, idxs=["modified", "is_default_page", "effective"]
        )
        self.portal.default_page = "published"
        self.portal.portal_catalog.reindexObject(
            self.portal.published, idxs=["modified", "is_default_page", "effective"]
        )
        logout()

        self.portal.REQUEST["page"] = 1
        xml = self.uncompress(self.sitemap())
        self.assertFalse("<loc>http://nohost/plone/folder/default</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/folder</loc>" in xml)
        self.assertTrue("<lastmod >2001-01-01T" in xml)
        self.assertTrue("<loc>http://nohost/plone</loc>" in xml)
        self.assertFalse("<loc>http://nohost/plone/published</loc>" in xml)

    def test_rendering_of_sitemap_index(self):
        """check that when calling without parameters,
        it renders a sitemap index file pointing to the specific files
        """
        # first round as an authenticated (manager)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)
        xml = self.uncompress(self.sitemap())

        self.assertTrue("<sitemapindex" in xml)
        self.assertTrue("<loc>http://nohost/plone/sitemap.xml.gz?page=1</loc>" in xml)
        self.assertTrue(
            "<loc>http://nohost/plone/sitemap.xml.gz?page=2</loc>" not in xml
        )

    def test_rendering_multiple_sitemaps(self):
        """test that when we have more than the batch size count items"""
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)

        # Generate 5000 items to have at least 2 sitemap URLs generated in the index file
        for count in range(5000):
            self.portal.invokeFactory(id=f"private-{count}", type_name="Document")

        xml = self.uncompress(self.sitemap())

        self.assertTrue("<sitemapindex" in xml)
        self.assertTrue("<loc>http://nohost/plone/sitemap.xml.gz?page=1</loc>" in xml)
        self.assertTrue("<loc>http://nohost/plone/sitemap.xml.gz?page=2</loc>" in xml)
        self.assertTrue(
            "<loc>http://nohost/plone/sitemap.xml.gz?page=3</loc>" not in xml
        )

    def test_first_page_has_batch_size_count_items(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        login(self.portal, TEST_USER_NAME)

        # Generate 5000 items to have at least 2 sitemap URLs generated in the index file
        for count in range(5000):
            self.portal.invokeFactory(id=f"private-{count}", type_name="Document")

        self.portal.REQUEST["page"] = 1

        xml = self.uncompress(self.sitemap())
        self.assertEqual(xml.count("<loc>"), 5000)

        # Now we try the second batch
        self.portal.REQUEST["page"] = 2

        xml = self.uncompress(self.sitemap())
        self.assertEqual(xml.count("<loc>"), 6)
