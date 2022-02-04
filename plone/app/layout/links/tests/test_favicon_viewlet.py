# -*- coding: utf-8 -*-
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.layout.testing import FUNCTIONAL_TESTING
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings
from zope.component import getUtility
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import ISecuritySchema, ISiteSchema
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.layout.links.viewlets import FaviconViewlet
from plone.formwidget.namedfile.converter import b64encode_file


class TestFaviconViewletView(ViewletsTestCase, FaviconViewlet):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = ''
        self.site_url = ''

    def test_FaviconViewlet_get_mimetype_svg(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = 'test.svg'
        file_data = 'Hello World'.encode()
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, 'image/svg+xml')

    def test_FaviconViewlet_get_mimetype_jpg(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = 'test.jpg'
        file_data = 'Hello World'.encode()
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, 'image/jpeg')

    def test_FaviconViewlet_get_mimetype_png(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = 'test.png'
        file_data = 'Hello World'.encode()
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, 'image/png')

    def test_FaviconViewlet_get_mimetype_ico(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = 'test.ico'
        file_data = 'Hello World'.encode()
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, 'image/vnd.microsoft.icon')

    def test_FaviconViewlet_get_mimetype_none(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        settings.site_favicon = None
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, 'image/vnd.microsoft.icon')
