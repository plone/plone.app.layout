from datetime import datetime
from datetime import timedelta
from plone.app.contenttypes.testing import (  # noqa
    PLONE_APP_CONTENTTYPES_FUNCTIONAL_TESTING,
)
from plone.app.contenttypes.testing import (  # noqa
    PLONE_APP_CONTENTTYPES_INTEGRATION_TESTING,
)
from plone.app.contenttypes.tests.test_image import dummy_image
from plone.app.layout.contenttypes.folder import FolderView
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser

import unittest


class FolderViewIntegrationTest(unittest.TestCase):
    layer = PLONE_APP_CONTENTTYPES_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        self.request["ACTUAL_URL"] = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])

    def test_result_filtering(self):
        """Test, if portal_state's friendly_types and the result method's
        keyword arguments are included in the query.
        """

        self.portal.invokeFactory("News Item", "newsitem")
        self.portal.invokeFactory("Document", "document")
        view = FolderView(self.portal, self.request)

        # Test, if all results are found.
        view.portal_state.friendly_types = lambda: ["Document", "News Item"]
        res = view.results()
        self.assertEqual(len(res), 2)

        # Test, if friendly_types does filter for types.
        view.portal_state.friendly_types = lambda: ["Document"]
        res = view.results()
        self.assertEqual(len(res), 1)

        # Test, if friendly_types does filter for types.
        view.portal_state.friendly_types = lambda: ["NotExistingType"]
        res = view.results()
        self.assertEqual(len(res), 0)

        # Test, if kwargs filtering is applied.
        view.portal_state.friendly_types = lambda: ["NotExistingType"]
        res = view.results(
            object_provides="plone.app.contenttypes.interfaces.IDocument"
        )
        self.assertEqual(len(res), 1)

    def test_result_batching(self):
        for idx in range(5):
            self.portal.invokeFactory("Document", f"document{idx}")
        request = self.request.clone()
        request.form["b_size"] = 5
        view = FolderView(self.portal, request)

        batch = view.batch()
        self.assertEqual(batch.length, 5)
        self.assertEqual(len([item for item in batch]), 5)
        self.assertFalse(batch.has_next)

        self.portal.invokeFactory("Document", "document5")

        batch = view.batch()
        self.assertEqual(batch.length, 6)
        self.assertEqual(len([item for item in batch]), 6)
        self.assertFalse(batch.has_next)

        self.portal.invokeFactory("Document", "document6")

        batch = view.batch()
        self.assertEqual(batch.length, 5)
        self.assertEqual(len([item for item in batch]), 5)
        self.assertTrue(batch.has_next)
        self.assertEqual(batch.next_item_count, 2)


class FolderViewFunctionalTest(unittest.TestCase):
    layer = PLONE_APP_CONTENTTYPES_FUNCTIONAL_TESTING

    def setUp(self):
        app = self.layer["app"]
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_url = self.portal.absolute_url()
        self.portal.invokeFactory("Folder", id="folder", title="My Folder")
        self.folder = self.portal.folder
        self.folder_url = self.folder.absolute_url()
        self.folder.invokeFactory("Document", id="doc1", title="Document 1")
        import transaction

        transaction.commit()
        self.browser = Browser(app)
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization",
            "Basic {}:{}".format(
                SITE_OWNER_NAME,
                SITE_OWNER_PASSWORD,
            ),
        )

    def test_folder_view(self):
        self.browser.open(self.folder_url + "/view")
        self.assertIn("My Folder", self.browser.contents)
        self.assertIn("Document 1", self.browser.contents)

    def test_folder_summary_view(self):
        self.browser.open(self.folder_url + "/summary_view")
        self.assertIn("My Folder", self.browser.contents)
        self.assertIn("Document 1", self.browser.contents)

    def test_folder_full_view(self):
        self.browser.open(self.folder_url + "/full_view")
        self.assertIn("My Folder", self.browser.contents)
        self.assertIn("Document 1", self.browser.contents)

    def test_folder_tabular_view(self):
        self.browser.open(self.folder_url + "/tabular_view")
        self.assertIn("My Folder", self.browser.contents)
        self.assertIn("Document 1", self.browser.contents)

    def test_folder_album_view(self):
        self.folder.invokeFactory("Image", id="image1", title="Image 1")
        img1 = self.folder["image1"]
        img1.image = dummy_image()
        import transaction

        transaction.commit()
        self.browser.open(self.folder_url + "/album_view")
        self.assertIn("My Folder", self.browser.contents)
        self.assertIn(
            '<img src="http://nohost/plone/folder/image1/@@images',
            self.browser.contents,
        )

    def test_list_item_wout_title(self):
        """In content listings, if a content object has no title use it's id."""
        self.folder.invokeFactory("Document", id="doc_wout_title")
        import transaction

        transaction.commit()

        # Document should be shown in listing view (and it's siblings)
        self.browser.open(self.folder_url + "/listing_view")
        self.assertIn("doc_wout_title", self.browser.contents)

        # And also in tabular view
        self.browser.open(self.folder_url + "/tabular_view")
        self.assertIn("doc_wout_title", self.browser.contents)

    def test_event_wout_location(self):
        # deactivate "plone.eventlocation" from Event behaviors
        event_fti = self.portal.portal_types.get("Event")
        if not event_fti:
            return
        event_behaviors = list(event_fti.behaviors)
        event_behaviors.remove("plone.eventlocation")
        event_fti.behaviors = tuple(event_behaviors)

        self.folder.invokeFactory(
            "Event",
            id="event_wout_location",
            title="Event without location",
            start=datetime.now() + timedelta(days=1),
        )

        import transaction

        transaction.commit()

        self.browser.open(self.folder_url + "/listing_view")
        self.assertIn("Event without location", self.browser.contents)
