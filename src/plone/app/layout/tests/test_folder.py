from DateTime import DateTime
from plone.app.content.testing import PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING
from plone.app.content.testing import PLONE_APP_CONTENT_DX_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.dexterity.fti import DexterityFTI
from plone.locking.interfaces import IRefreshableLockable
from plone.protect.authenticator import createToken
from plone.uuid.interfaces import IUUID
from Products.CMFCore.utils import getToolByName
from Testing.makerequest import makerequest
from transaction import commit
from urllib.parse import urlparse
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import alsoProvides
from zope.publisher.browser import TestRequest

import json
import unittest


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()

        self.request = TestRequest(
            environ={"HTTP_ACCEPT_LANGUAGE": "en", "REQUEST_METHOD": "POST"},
            form={
                "selection": '["' + IUUID(self.portal.page) + '"]',
                "_authenticator": createToken(),
                "folder": "/",
            },
        )
        self.request.REQUEST_METHOD = "POST"
        # Mock physicalPathFromURL
        # NOTE: won't return the right path in virtual hosting environments
        self.request.physicalPathFromURL = lambda url: urlparse(url).path.split(
            "/"
        )  # noqa
        alsoProvides(self.request, IAttributeAnnotatable)
        self.userList = "one,two"


class DXBaseTest(BaseTest):
    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        portal_types = getToolByName(self.portal, "portal_types")
        if "Document" not in portal_types.objectIds():
            fti = DexterityFTI("Document")
            portal_types._setObject("Document", fti)
        super().setUp()


class PropertiesDXTest(DXBaseTest):
    def testEffective(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["effectiveDate"] = "1999/01/01 09:00"
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.effective_date, DateTime("1999/01/01 09:00"))

    def testExpires(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["expirationDate"] = "1999/01/01 09:00"
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.expiration_date, DateTime("1999/01/01 09:00"))

    def testSetDexterityExcludeFromNav(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["exclude-from-nav"] = "yes"
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.exclude_from_nav, True)

    def testRights(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["copyright"] = "foobar"
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.rights, "foobar")

    def testContributors(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["contributors"] = self.userList
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.contributors, ("one", "two"))

    def testCreators(self):
        from plone.app.layout.content.browser.contents.properties import (  # noqa
            PropertiesActionView,
        )

        self.request.form["creators"] = self.userList
        view = PropertiesActionView(self.portal.page, self.request)
        view()
        self.assertEqual(self.portal.page.creators, ("one", "two"))


class WorkflowTest(BaseTest):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def convertDateTimeToIndexRepr(self, date):
        t_tup = date.toZone("UTC").parts()
        yr = t_tup[0]
        mo = t_tup[1]
        dy = t_tup[2]
        hr = t_tup[3]
        mn = t_tup[4]

        return (((yr * 12 + mo) * 31 + dy) * 24 + hr) * 60 + mn

    def testStateChange(self):
        from plone.app.layout.content.browser.contents.workflow import (  # noqa
            WorkflowActionView,
        )

        self.request.form["transition"] = "publish"
        default_effective = DateTime(f"1969/12/31 00:00:00 {DateTime().timezone()}")
        default_effective_index = self.convertDateTimeToIndexRepr(default_effective)
        pc = getToolByName(self.portal, "portal_catalog")
        # i need to call it, to populate catalog indexes
        pc()
        self.assertEqual(pc.uniqueValuesFor("effective"), (default_effective_index,))
        view = WorkflowActionView(self.portal.page, self.request)
        view()
        workflowTool = getToolByName(self.portal, "portal_workflow")
        self.assertEqual(
            workflowTool.getInfoFor(self.portal.page, "review_state"), "published"
        )
        # commit to update indexes in catalog
        commit()
        effective_index = self.convertDateTimeToIndexRepr(
            self.portal.page.effective_date
        )
        self.assertIn(effective_index, pc.uniqueValuesFor("effective"))


class RenameTest(BaseTest):
    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def test_folder_rename_objects(self):
        from plone.app.layout.content.browser.contents.rename import RenameActionView

        uid = IUUID(self.portal.page)
        self.portal.invokeFactory("Document", id="page2", title="2nd page")
        uid2 = IUUID(self.portal.page2)
        self.request.form.update(
            {
                "UID_0": uid,
                "newid_0": "I am UnSafe! ",
                "newtitle_0": "New!",
                "UID_1": uid2,
                "newid_1": ". ,;new id : _! ",
                "newtitle_1": "Newer!",
            }
        )
        view = RenameActionView(self.portal, self.request)
        view()
        self.assertEqual(self.portal["i-am-unsafe"].title, "New!")
        self.assertEqual(self.portal["new-id-_"].title, "Newer!")

    def test_default_page_updated_on_rename_objects(self):
        from plone.app.layout.content.browser.contents.rename import RenameActionView

        self.portal.setDefaultPage("page")
        uid = IUUID(self.portal.page)
        self.request.form.update(
            {"UID_0": uid, "newid_0": "page-renamed", "newtitle_0": "Page"}
        )
        view = RenameActionView(self.portal, self.request)
        view()
        self.assertEqual(self.portal.getDefaultPage(), "page-renamed")


class ContextInfoTest(BaseTest):
    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def testStateChange(self):
        from plone.app.layout.content.browser.contents import ContextInfo

        view = ContextInfo(self.portal.page, self.request)
        result = json.loads(view())
        self.assertEqual(result["object"]["Title"], "page")
        self.assertTrue(len(result["breadcrumbs"]) > 0)


class CutCopyLockedTest(BaseTest):
    """in folder contents"""

    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.portal.acl_users.userFolderAddUser(
            "editor", TEST_USER_PASSWORD, ["Editor"], []
        )

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()

        self.env = {"HTTP_ACCEPT_LANGUAGE": "en", "REQUEST_METHOD": "POST"}
        self.request = makerequest(self.layer["app"]).REQUEST
        self.request.environ.update(self.env)
        self.request.form = {
            "selection": '["' + IUUID(self.portal.page) + '"]',
            "_authenticator": createToken(),
            "folder": "/",
        }
        self.request.REQUEST_METHOD = "POST"

    def test_cut_object_when_locked_by_current_user(self):
        from plone.app.layout.content.browser.contents.cut import CutActionView

        plone_lock_info = self.portal.page.restrictedTraverse("@@plone_lock_info")
        lockable = IRefreshableLockable(self.portal.page)
        lockable.lock()
        self.assertTrue(plone_lock_info.is_locked())
        view = CutActionView(self.portal, self.request)
        view()
        self.assertEqual(len(view.errors), 0)
        self.assertFalse(plone_lock_info.is_locked())

    def test_cut_object_when_locked_by_other_user(self):
        from plone.app.layout.content.browser.contents.cut import CutActionView

        plone_lock_info = self.portal.page.restrictedTraverse("@@plone_lock_info")
        lockable = IRefreshableLockable(self.portal.page)
        lockable.lock()
        logout()

        login(self.portal, "editor")
        self.assertTrue(plone_lock_info.is_locked())
        self.request.form["_authenticator"] = createToken()
        view = CutActionView(self.portal, self.request)
        view()
        self.assertEqual(len(view.errors), 1)
        self.assertTrue(plone_lock_info.is_locked())


class DeleteDXTest(BaseTest):
    """Verify delete behavior from the folder contents view"""

    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.portal.acl_users.userFolderAddUser(
            "editor", TEST_USER_PASSWORD, ["Editor"], []
        )

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()

        self.env = {"HTTP_ACCEPT_LANGUAGE": "en", "REQUEST_METHOD": "POST"}
        self.request = makerequest(self.layer["app"]).REQUEST
        self.request.environ.update(self.env)
        self.request.form = {
            "selection": '["' + IUUID(self.portal.page) + '"]',
            "_authenticator": createToken(),
            "folder": "/",
        }
        self.request.REQUEST_METHOD = "POST"

    def make_request(self):
        request = makerequest(self.layer["app"], environ=self.env).REQUEST
        self.request.environ.update(self.env)
        request.REQUEST_METHOD = "POST"
        return request

    def test_delete_object(self):
        from plone.app.layout.content.browser.contents.delete import DeleteActionView

        page_id = self.portal.page.id
        self.assertTrue(page_id in self.portal)
        view = DeleteActionView(self.portal, self.request)
        view()
        self.assertTrue(page_id not in self.portal)

    def test_delete_object_when_locked_by_current_user(self):
        from plone.app.layout.content.browser.contents.delete import DeleteActionView

        page_id = self.portal.page.id
        lockable = IRefreshableLockable(self.portal.page)
        lockable.lock()
        view = DeleteActionView(self.portal, self.request)
        view()
        self.assertEqual(len(view.errors), 0)
        self.assertTrue(page_id not in self.portal)

    def test_delete_object_when_locked_by_other_user(self):
        from plone.app.layout.content.browser.contents.delete import DeleteActionView

        plone_lock_info = self.portal.page.restrictedTraverse("@@plone_lock_info")
        lockable = IRefreshableLockable(self.portal.page)
        lockable.lock()
        logout()

        login(self.portal, "editor")
        self.assertTrue(plone_lock_info.is_locked())
        self.request.form["_authenticator"] = createToken()
        view = DeleteActionView(self.portal, self.request)
        view()
        self.assertEqual(len(view.errors), 1)
        self.assertTrue(plone_lock_info.is_locked())

    def test_delete_wrong_object_by_acquisition(self):
        page_id = self.portal.page.id
        f1 = self.portal.invokeFactory("Folder", id="f1", title="folder one")
        # created a nested page with the same id as the one at the site root
        p1 = self.portal[f1].invokeFactory("Document", id=page_id, title="page")
        self.assertEqual(p1, page_id)
        request2 = self.make_request()

        # both pages exist before we delete on
        for location in [self.portal, self.portal[f1]]:
            self.assertTrue(p1 in location)

        # instantiate two different views and delete the same object with each
        from plone.app.layout.content.browser.contents.delete import DeleteActionView

        object_uuid = IUUID(self.portal[f1][p1])
        for req in [self.request, request2]:
            req.form = {
                "selection": f'["{object_uuid}"]',
                "_authenticator": createToken(),
                "folder": f"/{f1}/",
            }
            view = DeleteActionView(self.portal, req)
            view()

        # the root page exists, the nested one is gone
        self.assertTrue(p1 in self.portal)
        self.assertFalse(p1 in self.portal[f1])


class RearrangeDXTest(BaseTest):
    """Verify rearrange feature from the folder contents view"""

    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.portal.invokeFactory("Folder", id="basefolder", title="Folder Base")
        self.bf = self.portal.basefolder
        self.bf.reindexObject()
        for idx in range(0, 5):
            newid = f"f{idx}"
            self.bf.invokeFactory(
                "Folder",
                id=newid,
                # title in reverse order
                title=f"Folder {4 - idx}",
            )
            self.bf[newid].reindexObject()

        # create 3 documents in plone root
        for idx in range(0, 3):
            _id = f"page_{idx}"
            self.portal.invokeFactory("Document", id=_id, title=f"Page {idx}")
            self.portal[_id].reindexObject()

        self.env = {"HTTP_ACCEPT_LANGUAGE": "en", "REQUEST_METHOD": "POST"}
        self.request = makerequest(self.layer["app"]).REQUEST
        self.request.environ.update(self.env)
        self.request.form = {
            "selection": '["' + IUUID(self.bf) + '"]',
            "_authenticator": createToken(),
            "folder": "/basefolder",
        }
        self.request.REQUEST_METHOD = "POST"

    def test_initial_order(self):
        # just to be sure preconditions are fine
        #
        # initial ids are forward
        # and titles are set reversed!
        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.bf.contentItems()],
            [
                ("f0", "Folder 4"),
                ("f1", "Folder 3"),
                ("f2", "Folder 2"),
                ("f3", "Folder 1"),
                ("f4", "Folder 0"),
            ],
        )

    def test_rearrange_by_title(self):
        from plone.app.layout.content.browser.contents.rearrange import (  # noqa
            RearrangeActionView,
        )

        self.request.form.update(
            {
                "rearrange_on": "sortable_title",
            }
        )
        view = RearrangeActionView(self.bf, self.request)
        view()
        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.bf.contentItems()],
            [
                ("f4", "Folder 0"),
                ("f3", "Folder 1"),
                ("f2", "Folder 2"),
                ("f1", "Folder 3"),
                ("f0", "Folder 4"),
            ],
        )

    def test_item_order_move_to_top(self):
        from plone.app.layout.content.browser.contents.rearrange import (  # noqa
            ItemOrderActionView,
        )

        self.request.form.update(
            {
                "id": "f2",
                "delta": "top",
            }
        )
        view = ItemOrderActionView(self.bf, self.request)
        view()
        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.bf.contentItems()],
            [
                ("f2", "Folder 2"),
                ("f0", "Folder 4"),
                ("f1", "Folder 3"),
                ("f3", "Folder 1"),
                ("f4", "Folder 0"),
            ],
        )

    def test_item_order_move_to_bottom(self):
        from plone.app.layout.content.browser.contents.rearrange import (  # noqa
            ItemOrderActionView,
        )

        self.request.form.update(
            {
                "id": "f2",
                "delta": "bottom",
            }
        )
        view = ItemOrderActionView(self.bf, self.request)
        view()
        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.bf.contentItems()],
            [
                ("f0", "Folder 4"),
                ("f1", "Folder 3"),
                ("f3", "Folder 1"),
                ("f4", "Folder 0"),
                ("f2", "Folder 2"),
            ],
        )

    def test_item_order_move_by_delta(self):
        from plone.app.layout.content.browser.contents.rearrange import (  # noqa
            ItemOrderActionView,
        )

        self.request.form.update(
            {
                "id": "f2",
                "delta": "-1",
            }
        )
        view = ItemOrderActionView(self.bf, self.request)
        view()
        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.bf.contentItems()],
            [
                ("f0", "Folder 4"),
                ("f2", "Folder 2"),
                ("f1", "Folder 3"),
                ("f3", "Folder 1"),
                ("f4", "Folder 0"),
            ],
        )

    def test_item_order_move_by_delta_in_plone_root(self):
        from plone.app.layout.content.browser.contents.rearrange import (  # noqa
            ItemOrderActionView,
        )

        # first move the 'basefolder' to the top
        self.request.form.update(
            {
                "id": "basefolder",
                "delta": "top",
            }
        )
        view = ItemOrderActionView(self.portal, self.request)
        view()

        # move 'basefolder' two positions down
        self.request.form.update(
            {
                "id": "basefolder",
                "delta": "2",
                "subsetIds": '["basefolder", "page_0", "page_1", "page_2"]',
            }
        )
        view = ItemOrderActionView(self.portal, self.request)
        view()

        self.assertEqual(
            [(c[0], c[1].Title()) for c in self.portal.contentItems()],
            [
                ("page_0", "Page 0"),
                ("page_1", "Page 1"),
                ("basefolder", "Folder Base"),
                ("page_2", "Page 2"),
            ],
        )


class FolderFactoriesTest(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_folder_factories_regression(self):
        from plone.app.layout.content.browser.folderfactories import FolderFactoriesView as FFV

        view = FFV(self.portal, self.request)
        self.request.form.update(
            {"form.button.Add": "yes", "url": self.portal.absolute_url()}
        )
        view()
        self.assertEqual(
            self.request.response.headers.get("location"), self.portal.absolute_url()
        )

    def test_folder_factories(self):
        from plone.app.layout.content.browser.folderfactories import FolderFactoriesView as FFV

        view = FFV(self.portal, self.request)
        self.request.form.update(
            {"form.button.Add": "yes", "url": "http://www.foobar.com"}
        )
        view()
        self.assertNotEqual(
            self.request.response.headers.get("location"), "http://www.foobar.com"
        )
