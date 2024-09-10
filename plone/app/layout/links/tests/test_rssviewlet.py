from plone.app.layout.links.viewlets import RSSViewlet
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.base.interfaces import ISiteSyndicationSettings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import re


class TestRSSViewletView(ViewletsTestCase):
    def test_RSSViewlet(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory("Folder", "news")
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSyndicationSettings)
        if settings.allowed:
            # make sure syndication is disabled
            settings.allowed = False
        request = self.app.REQUEST
        viewlet = RSSViewlet(self.portal, request, None, None)
        viewlet.update()
        result = viewlet.render()
        self.assertEqual(result.strip(), "")
        settings.allowed = True
        settings.site_rss_items = (self.portal.news.UID(),)
        request = self.app.REQUEST
        viewlet = RSSViewlet(self.portal, request, None, None)
        viewlet.update()
        result = viewlet.render()
        self.assertFalse("<link" not in result)
        self.assertFalse("http://nohost/plone/atom.xml" not in result)
        self.assertFalse("http://nohost/plone/news/atom.xml" not in result)

    def test_RSSViewlet_with_private_objs(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory("Folder", "news")
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSyndicationSettings)
        self.assertTrue(settings.allowed)

        # Stream a private folder
        self.portal.news.invokeFactory("Collection", "aggregator")
        settings.site_rss_items = (self.portal.news.aggregator.UID(),)
        request = self.layer["request"]

        link_href_pattern = re.compile(r'<link href="(.*?)"')

        # Verify that anonymous users can't see the RSS feed
        # from the aggregator collection
        logout()
        viewlet = RSSViewlet(self.portal, request.clone(), None, None)
        viewlet.update()
        result = viewlet.render()

        self.assertSetEqual(
            {
                "http://nohost/plone/atom.xml",
                "http://nohost/plone/rss.xml",
                "http://nohost/plone/RSS",
            },
            {match.group(1) for match in link_href_pattern.finditer(result)},
        )

        login(self.portal, TEST_USER_NAME)
        viewlet = RSSViewlet(self.portal, request.clone(), None, None)
        viewlet.update()
        result = viewlet.render()

        # Verify that an authenticated user can see the RSS feed
        # from the aggregator collection
        self.assertSetEqual(
            {
                "http://nohost/plone/atom.xml",
                "http://nohost/plone/rss.xml",
                "http://nohost/plone/RSS",
                "http://nohost/plone/news/aggregator/atom.xml",
                "http://nohost/plone/news/aggregator/rss.xml",
                "http://nohost/plone/news/aggregator/RSS",
            },
            {match.group(1) for match in link_href_pattern.finditer(result)},
        )
