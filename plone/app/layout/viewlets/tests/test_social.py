from plone.app.layout.viewlets.social import SocialTagsViewlet
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.base.interfaces import ISocialMediaSchema
from plone.registry.interfaces import IRegistry
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility


class TestSocialViewlet(ViewletsTestCase):
    """Test the content views viewlet."""

    def setUp(self):
        super().setUp()
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.folder.invokeFactory("News Item", "news-item", title="News Item")
        self.news = self.folder["news-item"]
        logout()

    def _tagFound(self, tags, attr, name=None, value=None):
        for meta in tags:
            if attr in meta:
                if name is None:
                    # only checking for existence
                    return True
                if meta[attr] == name:
                    if value is None:
                        # only checking for existence
                        return True
                    return meta["content"] == value
        return False

    def tagFound(self, viewlet, attr, name=None, value=None):
        return self._tagFound(viewlet.tags, attr, name=name, value=value)

    def bodyTagFound(self, viewlet, attr, name=None, value=None):
        return self._tagFound(viewlet.body_tags, attr, name=name, value=value)

    def testBasicTags(self):
        viewlet = SocialTagsViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        description = self.folder.Description()
        folder_url = self.folder.absolute_url()
        # Twitter
        self.assertTrue(self.tagFound(viewlet, "name", "twitter:card", "summary"))
        # OpenGraph/Facebook
        self.assertTrue(
            self.tagFound(
                viewlet, "property", "og:site_name", viewlet.site_title_setting
            )
        )
        self.assertTrue(
            self.tagFound(viewlet, "property", "og:title", viewlet.page_title)
        )
        self.assertTrue(
            self.tagFound(viewlet, "property", "og:description", description)
        )
        self.assertTrue(self.tagFound(viewlet, "property", "og:url", folder_url))
        # No schema.org itemprops
        self.assertFalse(self.tagFound(viewlet, "itemprop"))

    def testBasicItemProps(self):
        viewlet = SocialTagsViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        description = self.folder.Description()
        folder_url = self.folder.absolute_url()
        # No Twitter
        self.assertFalse(self.bodyTagFound(viewlet, "name"))
        # No OpenGraph/Facebook
        self.assertFalse(self.bodyTagFound(viewlet, "property"))
        # schema.org itemprops
        self.assertTrue(
            self.bodyTagFound(viewlet, "itemprop", "name", viewlet.page_title)
        )
        self.assertTrue(
            self.bodyTagFound(viewlet, "itemprop", "description", description)
        )
        self.assertTrue(self.bodyTagFound(viewlet, "itemprop", "url", folder_url))

    def testDisabled(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISocialMediaSchema, prefix="plone", check=False
        )
        settings.share_social_data = False
        viewlet = SocialTagsViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(len(viewlet.tags), 0)

    def testDisabledForLoggedUser(self):
        login(self.portal, TEST_USER_NAME)
        viewlet = SocialTagsViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(len(viewlet.tags), 0)
        # clear cache to prevent memoize
        cache = IAnnotations(self.app.REQUEST)
        key = "plone.memoize"
        cache[key] = {}
        logout()
        viewlet.update()
        self.assertTrue(len(viewlet.tags) > 1)

    def testIncludeSocialSettings(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISocialMediaSchema, prefix="plone", check=False
        )
        settings.twitter_username = "foobar"
        settings.facebook_app_id = "foobar"
        settings.facebook_username = "foobar"
        viewlet = SocialTagsViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertTrue(self.tagFound(viewlet, "name", "twitter:site", "@foobar"))
        self.assertTrue(self.tagFound(viewlet, "property", "fb:app_id", "foobar"))
        self.assertTrue(
            self.tagFound(
                viewlet,
                "property",
                "og:article:publisher",
                "https://www.facebook.com/foobar",
            )
        )

    def testLogo(self):
        viewlet = SocialTagsViewlet(self.news, self.app.REQUEST, None)
        viewlet.update()
        self.assertTrue(
            self.tagFound(
                viewlet,
                "property",
                "og:image",
                "http://nohost/plone/++resource++plone-logo.svg",
            )
        )
        self.assertFalse(self.tagFound(viewlet, "itemprop"))
        self.assertTrue(
            self.bodyTagFound(
                viewlet,
                "itemprop",
                "image",
                "http://nohost/plone/++resource++plone-logo.svg",
            )
        )
