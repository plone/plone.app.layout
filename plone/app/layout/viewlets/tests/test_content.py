from DateTime import DateTime
from plone.app.layout.viewlets.content import ContentRelatedItems
from plone.app.layout.viewlets.content import DocumentBylineViewlet
from plone.app.layout.viewlets.content import HistoryByLineView
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_PASSWORD
from plone.base.interfaces import ISecuritySchema
from plone.base.interfaces import ISiteSchema
from plone.dexterity.fti import DexterityFTI
from plone.locking.interfaces import ILockable
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.interface import Interface
from zope.intid.interfaces import IIntIds


class IMyDexterityItem(Interface):
    """Dexterity test type"""


class TestDocumentBylineViewletView(ViewletsTestCase):
    """
    Test the document by line viewlet
    """

    def setUp(self):
        super().setUp()
        self.folder.invokeFactory("Document", "doc1", title="Document 1")
        self.context = self.folder["doc1"]

        registry = getUtility(IRegistry)
        self.site_settings = registry.forInterface(
            ISiteSchema,
            prefix="plone",
        )
        self.security_settings = registry.forInterface(
            ISecuritySchema,
            prefix="plone",
        )

    def _get_viewlet(self):
        request = self.app.REQUEST
        viewlet = DocumentBylineViewlet(self.context, request, None, None)
        viewlet.update()
        return viewlet

    def test_get_memberinfo(self):
        viewlet = self._get_viewlet()
        self.assertIsNone(viewlet.get_member_info("bogus"))
        self.assertIsInstance(viewlet.get_member_info("test_user_1_"), dict)

    def test_get_url_path(self):
        viewlet = self._get_viewlet()
        self.assertEqual(viewlet.get_url_path("bogus"), "")
        self.assertEqual(viewlet.get_url_path("test_user_1_"), "author/test_user_1_")

        # users with a slash in the userid will have a different URL
        portal_membership = getToolByName(self.portal, "portal_membership")
        portal_membership.addMember("foo/bar", TEST_USER_PASSWORD, ["Member"], "")
        self.assertEqual(viewlet.get_url_path("foo/bar"), "author/?author=foo%2Fbar")

    def test_get_fullname(self):
        viewlet = self._get_viewlet()
        # For non existent user we return the user id
        self.assertEqual(viewlet.get_fullname("bogus"), "bogus")
        # If the fullname is not set we return the user id
        self.assertEqual(viewlet.get_fullname("test_user_1_"), "test_user_1_")

        # otherwise we will return the fullname property
        portal_membership = getToolByName(self.portal, "portal_membership")
        portal_membership.addMember(
            "foo/bar",
            TEST_USER_PASSWORD,
            ["Member"],
            "",
            properties={"fullname": "Foo Bar"},
        )
        self.assertEqual(viewlet.get_fullname("foo/bar"), "Foo Bar")

    def test_pub_date(self):
        # configure our portal to enable publication date on pages globally on
        # the site
        self.site_settings.display_publication_date_in_byline = True

        logout()
        viewlet = self._get_viewlet()

        # publication date should be None as there is not Effective date set
        # for our document yet
        self.assertEqual(viewlet.pub_date(), None)

        # now set effective date for our document
        effective = DateTime()
        self.context.setEffectiveDate(effective)
        self.assertEqual(viewlet.pub_date(), DateTime(effective.ISO8601()))

        # now switch off publication date globally on the site and see if
        # viewlet returns None for publication date
        self.site_settings.display_publication_date_in_byline = False
        self.assertEqual(viewlet.pub_date(), None)

    def test_anonymous_users_see_byline_if_show_enabled(self):
        self.site_settings.display_publication_date_in_byline = True
        logout()
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_anonymous_users_dont_see_byline_if_show_disabled(self):
        self.site_settings.display_publication_date_in_byline = False
        logout()
        viewlet = self._get_viewlet()
        self.assertFalse(viewlet.show())

    def test_logged_users_see_byline_if_show_enabled(self):
        self.site_settings.display_publication_date_in_byline = True
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_logged_users_see_byline_if_show_disabled(self):
        self.site_settings.display_publication_date_in_byline = False
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_anonymous_users_see_about_if_show_enabled(self):
        self.security_settings.allow_anon_views_about = True
        logout()
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show_about())

    def test_anonymous_users_dont_see_about_if_show_disabled(self):
        self.security_settings.allow_anon_views_about = False
        logout()
        viewlet = self._get_viewlet()
        self.assertFalse(viewlet.show_about())

    def test_logged_users_see_about_if_show_enabled(self):
        self.security_settings.allow_anon_views_about = True
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show_about())

    def test_logged_users_see_about_if_show_disabled(self):
        self.security_settings.allow_anon_views_about = False
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show_about())


class TestHistoryBylineViewletView(ViewletsTestCase):
    """
    Test the document by line viewlet
    """

    def setUp(self):
        super().setUp()
        self.folder.invokeFactory("Document", "doc1", title="Document 1")
        self.context = self.folder["doc1"]

        registry = getUtility(IRegistry)
        self.security_settings = registry.forInterface(
            ISecuritySchema,
            prefix="plone",
        )

    def _get_viewlet(self):
        request = self.app.REQUEST
        viewlet = HistoryByLineView(self.context, request)
        viewlet.update()
        return viewlet

    def test_show_anonymous_not_allowed(self):
        self.security_settings.allow_anon_views_about = False
        logout()
        viewlet = self._get_viewlet()
        self.assertFalse(viewlet.show())

    def test_show_anonymous_allowed(self):
        self.security_settings.allow_anon_views_about = True
        logout()
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_show_logged_in_anonymous_not_allowed(self):
        self.security_settings.allow_anon_views_about = False
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_show_logged_in_anonymous_allowed(self):
        self.security_settings.allow_anon_views_about = True
        viewlet = self._get_viewlet()
        self.assertTrue(viewlet.show())

    def test_anonymous_locked_icon_not_locked(self):
        logout()
        viewlet = self._get_viewlet()
        self.assertEqual(viewlet.locked_icon(), "")

    def test_anonymous_locked_icon_is_locked(self):
        logout()
        ILockable(self.context).lock()
        viewlet = self._get_viewlet()
        self.assertEqual(viewlet.locked_icon(), "")

    def test_logged_in_locked_icon_not_locked(self):
        viewlet = self._get_viewlet()
        self.assertEqual(viewlet.locked_icon(), "")

    def test_logged_in_locked_icon_is_locked(self):
        viewlet = self._get_viewlet()
        ILockable(self.context).lock()
        lockIconUrl = '<img src="http://nohost/plone/lock_icon.png" alt="" \
title="Locked" height="16" width="16" />'
        self.assertEqual(viewlet.locked_icon(), lockIconUrl)

    def test_pub_date(self):
        # configure our portal to enable publication date on pages globally on
        # the site
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")

        settings.display_publication_date_in_byline = True

        logout()
        viewlet = self._get_viewlet()

        # publication date should be None as there is not Effective date set
        # for our document yet
        self.assertEqual(viewlet.pub_date(), None)

        # now set effective date for our document
        effective = DateTime()
        self.context.setEffectiveDate(effective)
        self.assertEqual(viewlet.pub_date(), DateTime(effective.ISO8601()))

        # now switch off publication date globally on the site and see if
        # viewlet returns None for publication date
        settings.display_publication_date_in_byline = False
        self.assertEqual(viewlet.pub_date(), None)


class TestRelatedItemsViewlet(ViewletsTestCase):
    def setUp(self):
        super().setUp()
        self.folder.invokeFactory("Document", "doc1", title="Document 1")
        self.folder.invokeFactory("Document", "doc2", title="Document 2")
        self.folder.invokeFactory("Document", "doc3", title="Document 3")
        intids = getUtility(IIntIds)
        self.folder.doc1.relatedItems = [
            RelationValue(intids.getId(self.folder.doc2)),
            RelationValue(intids.getId(self.folder.doc3)),
        ]

    def testRelatedItems(self):
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.doc1, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.Title for x in related], ["Document 2", "Document 3"])

    def testDeletedRelatedItems(self):
        # Deleted related items should not cause problems.
        self.folder._delObject("doc2")
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.doc1, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.Title for x in related], ["Document 3"])


class TestDexterityRelatedItemsViewlet(ViewletsTestCase):
    def setUp(self):
        super().setUp()
        """ create some sample content to test with """
        from plone.base.utils import get_installer

        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        fti = DexterityFTI("Dexterity Item with relatedItems behavior")
        self.portal.portal_types._setObject(
            "Dexterity Item with relatedItems behavior", fti
        )
        fti.klass = "plone.dexterity.content.Item"
        test_module = "plone.app.layout.viewlets.tests.test_content"
        fti.schema = test_module + ".IMyDexterityItem"
        fti.behaviors = ("plone.app.relationfield.behavior.IRelatedItems",)
        fti = DexterityFTI("Dexterity Item without relatedItems behavior")
        self.portal.portal_types._setObject(
            "Dexterity Item without relatedItems behavior", fti
        )
        fti.klass = "plone.dexterity.content.Item"
        fti.schema = test_module + ".IMyDexterityItem"
        self.folder.invokeFactory("Document", "doc1", title="Document 1")
        self.folder.invokeFactory("Document", "doc2", title="Document 2")
        self.folder.invokeFactory("Dexterity Item with relatedItems behavior", "dex1")
        self.folder.invokeFactory("Dexterity Item with relatedItems behavior", "dex2")
        self.folder.invokeFactory(
            "Dexterity Item without relatedItems behavior", "dex3"
        )
        qi = get_installer(self.portal)
        qi.install_product("plone.app.intid")
        intids = getUtility(IIntIds)
        self.folder.dex1.relatedItems = [
            RelationValue(intids.getId(self.folder.doc1)),
            RelationValue(intids.getId(self.folder.doc2)),
        ]

    def testDexterityRelatedItems(self):
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.dex1, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.id for x in related], ["doc1", "doc2"])

        # TODO: we should test with non-published objects and anonymous
        #       users but current workflow has no transition to make an
        #       item private

    def testDexterityEmptyRelatedItems(self):
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.dex2, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual(len(related), 0)

    def testDexterityWithoutRelatedItemsBehavior(self):
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.dex2, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual(len(related), 0)

    def testDexterityFolderRelatedItems(self):
        """
        Related items viewlet doesn't include related folder's descendants.
        """
        self.assertTrue(self.folder.contentValues(), "Folder is missing descendants")

        intids = getUtility(IIntIds)
        self.folder.dex1.relatedItems = [RelationValue(intids.getId(self.folder))]

        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.dex1, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual(len(related), 1)

    def testDexterityDeletedRelatedItems(self):
        # Deleted related items should not cause problems.
        self.folder._delObject("doc1")
        request = self.app.REQUEST
        viewlet = ContentRelatedItems(self.folder.dex1, request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.id for x in related], ["doc2"])
