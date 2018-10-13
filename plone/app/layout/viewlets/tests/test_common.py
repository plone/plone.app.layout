# -*- coding: utf-8 -*-
from plone.app.layout.navigation.interfaces import INavigationRoot
from plone.app.layout.viewlets.common import ContentViewsViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.app.layout.viewlets.common import LogoViewlet
from plone.app.layout.viewlets.common import TitleViewlet
from plone.app.layout.viewlets.common import ViewletBase
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.protect import authenticator as auth
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import INonStructuralFolder
from Products.CMFPlone.interfaces import ISiteSchema
from zope.component import getUtility
from zope.component.hooks import setSite
from zope.interface import alsoProvides
from zope.interface import directlyProvides
from zope.interface import noLongerProvides


# Red pixel with filename pixel.png
SITE_LOGO_BASE64 = b'filenameb64:cGl4ZWwucG5n;datab64:iVBORw0KGgoAAAANSUhEUgA'\
                   b'AAAEAAAABCAIAAACQd1PeAAAADElEQVQI12P4z8AAAAMBAQAY3Y2wAAA'\
                   b'AAElFTkSuQmCC'


class TestViewletBase(ViewletsTestCase):
    """Test the base class for the viewlets.
    """

    def test_update(self):
        request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.portal.invokeFactory('Folder', 'f1')
        context = getattr(self.portal, 'f1')
        alsoProvides(context, INavigationRoot)
        viewlet = ViewletBase(context, request, None, None)
        viewlet.update()
        self.assertEqual(viewlet.site_url, "http://nohost/plone")
        self.assertEqual(viewlet.navigation_root_url, "http://nohost/plone/f1")


class TestContentViewsViewlet(ViewletsTestCase):
    """Test the content views viewlet.
    """

    def setUp(self):
        super(TestContentViewsViewlet, self).setUp()
        self.folder.invokeFactory('Document', 'test',
                                  title='Test default page')
        self.folder.title = u"Folder"

    def _invalidateRequestMemoizations(self):
        try:
            del self.app.REQUEST.__annotations__
        except AttributeError:
            pass

    def test_set1_on_portal_root(self):
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = self.portal.absolute_url()
        view = ContentViewsViewlet(self.portal, self.app.REQUEST, None)
        view.update()
        self.assertEqual(view.tabSet1[0]['id'], 'folderContents')

    def test_set1_NonStructuralFolder(self):
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = self.folder.absolute_url()
        directlyProvides(self.folder, INonStructuralFolder)
        view = ContentViewsViewlet(self.folder, self.app.REQUEST, None)
        view.update()
        noLongerProvides(self.folder, INonStructuralFolder)
        self.assertEqual(1, len([t for t in view.tabSet1 if t[
                         'id'] == 'folderContents']))

    def test_set1(self):
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = '%s/edit?_authenticator=%s' % (
            self.folder.test.absolute_url(),
            auth.createToken()
        )
        view = ContentViewsViewlet(self.folder.test, self.app.REQUEST, None)
        view.update()
        self.assertEqual(
            1, len([t for t in view.tabSet1 if t['id'] == 'folderContents']))
        self.assertEqual(
            ['edit'], [t['id'] for t in view.tabSet1 if t['selected']])


class TestTitleViewsViewlet(ViewletsTestCase):
    """Test the title viewlet.
    """

    def setUp(self):
        super(TestTitleViewsViewlet, self).setUp()
        self.folder.invokeFactory('Document', 'test',
                                  title='Test default page')
        self.folder.title = u"Folder"

    def _invalidateRequestMemoizations(self):
        try:
            del self.app.REQUEST.__annotations__
        except AttributeError:
            pass

    def test_title_viewlet_on_portal(self):
        """Title viewlet renders navigation root title
        """
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = self.portal.absolute_url()
        viewlet = TitleViewlet(self.portal, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(viewlet.site_title, 'Plone site')
        registry = getUtility(IRegistry)
        site_settings = registry.forInterface(
            ISiteSchema, prefix='plone', check=False)
        site_settings.site_title = u'Süper Site'
        self._invalidateRequestMemoizations()
        viewlet.update()
        self.assertEqual(viewlet.site_title, u'S\xfcper Site')

    def test_title_viewlet_on_content(self):
        """Title viewlet renders navigation root title
        """
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = self.folder.test.absolute_url()
        viewlet = TitleViewlet(self.folder.test, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(viewlet.site_title,
                         'Test default page &mdash; Plone site')
        registry = getUtility(IRegistry)
        site_settings = registry.forInterface(
            ISiteSchema, prefix="plone", check=False)
        site_settings.site_title = u'Süper Site'
        self._invalidateRequestMemoizations()
        viewlet.update()
        self.assertEqual(viewlet.site_title,
                         u'Test default page &mdash; S\xfcper Site')

    def test_title_viewlet_with_navigation_root(self):
        """Title viewlet renders navigation root title
        """
        self._invalidateRequestMemoizations()
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Member'])
        self.app.REQUEST['ACTUAL_URL'] = self.folder.test.absolute_url()
        directlyProvides(self.folder, INavigationRoot)
        viewlet = TitleViewlet(self.folder.test, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(viewlet.site_title,
                         u'Test default page &mdash; Folder')


class TestLogoViewlet(ViewletsTestCase):
    """Test the site logo viewlet.
    """

    def _set_site(self, context):
        """Set context as a site.
        """
        # Set the portal's getSiteManager method on context.
        # This is a hackish way to make setSite work without creating a site
        # with five.localsitemanager.
        # ATTENTION: this works only for the purpose of this test.
        context.getSiteManager = self.portal.getSiteManager
        setSite(context)

    def test_logo_viewlet_portal_root_default(self):
        """When no logo is set, and viewlet is opened on a non-navigation root,
        obtain the default one from the portal.
        """
        viewlet = LogoViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(
            viewlet.img_src, '{0}/logo.png'.format(self.portal.absolute_url()))

    def test_logo_viewlet_portal_root_registry(self):
        """When a logo is set, and viewlet is opened on a non-navigation root,
        obtain the registry logo from the portal.
        """
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix='plone')
        settings.site_logo = SITE_LOGO_BASE64

        viewlet = LogoViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertTrue(
            viewlet.img_src,
            '{0}/@@site-logo/pixel.png'.format(self.portal.absolute_url())
        )

    def test_logo_viewlet_navigation_root_default(self):
        """When no logo is set, and viewlet is opened on a navigation root,
        obtain the default one from the navigation root.
        """
        self._set_site(self.folder)
        viewlet = LogoViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertEqual(
            viewlet.img_src, '{0}/logo.png'.format(self.folder.absolute_url()))

    def test_viewlet_navigation_root_registry(self):
        """When a logo is set, and viewlet is opened on a navigation root,
        obtain the registry logo from the navigation root.
        """
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix='plone')
        settings.site_logo = SITE_LOGO_BASE64

        # Set fake site after registry setup...
        self._set_site(self.folder)
        viewlet = LogoViewlet(self.folder, self.app.REQUEST, None)
        viewlet.update()
        self.assertTrue(
            viewlet.img_src,
            '{0}/@@site-logo/pixel.png'.format(self.folder.absolute_url())
        )


class TestGlobalSectionsViewlet(ViewletsTestCase):
    """Test the global sections views viewlet.
    """

    def test_selectedtabs(self):
        """ Test selected tabs the simplest case
        """
        request = self.layer['request']
        request['URL'] = self.folder.absolute_url()
        gsv = GlobalSectionsViewlet(self.folder, request, None)
        gsv.update()
        self.assertEqual(gsv.selected_tabs, {'portal': 'Members'})
        self.assertEqual(gsv.selected_portal_tab, 'Members')

    def test_selectedtabs_navroot(self):
        """ Test selected tabs with a INavigationroot folder involved
        """
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.invokeFactory('Folder', 'navroot', title='My new root')
        navroot = self.portal['navroot']
        alsoProvides(navroot, INavigationRoot)
        navroot.invokeFactory('Folder', 'abc', title='short')
        navroot.invokeFactory('Folder',
                              'xyz',
                              title='Folder with a looong name')
        request = self.layer['request']
        request['URL'] = navroot['abc'].absolute_url()
        gsv = GlobalSectionsViewlet(navroot, request, None)
        gsv.update()
        self.assertEqual(gsv.selected_tabs, {'portal': 'abc'})
        self.assertEqual(gsv.selected_portal_tab, 'abc')
