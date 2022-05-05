from plone.app.layout.links.viewlets import FaviconViewlet
from plone.app.layout.testing import FUNCTIONAL_TESTING
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.formwidget.namedfile.converter import b64encode_file
from plone.registry.interfaces import IRegistry
from plone.base.interfaces import ISiteSchema
from zope.component import getUtility


class TestFaviconViewletView(ViewletsTestCase, FaviconViewlet):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = ""
        self.site_url = ""

    def test_FaviconViewlet_get_mimetype_svg(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = "test.svg"
        file_data = b"Hello World"
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, "image/svg+xml")

    def test_FaviconViewlet_get_mimetype_jpg(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = "test.jpg"
        file_data = b"Hello World"
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, "image/jpeg")

    def test_FaviconViewlet_get_mimetype_png(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = "test.png"
        file_data = b"Hello World"
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, "image/png")

    def test_FaviconViewlet_get_mimetype_ico(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        filename = "test.ico"
        file_data = b"Hello World"
        encoded_data = b64encode_file(filename=filename, data=file_data)
        settings.site_favicon = encoded_data
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, "image/vnd.microsoft.icon")

    def test_FaviconViewlet_get_mimetype_none(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone")
        settings.site_favicon = None
        mimetype = settings.site_favicon_mimetype
        self.assertEqual(mimetype, "image/vnd.microsoft.icon")
