from plone.app.testing import login
from plone.app.layout.testing import INTEGRATION_TESTING
from zope.component import getMultiAdapter

import unittest


class TestSharingView(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

        self.portal.acl_users._doAddUser("testuser", "secret", ["Member"], [])
        self.portal.acl_users._doAddUser("testreviewer", "secret", ["Reviewer"], [])
        self.portal.acl_users._doAddUser("nonasciiuser", "secret", ["Member"], [])
        self.portal.acl_users._doAddGroup(
            "testgroup", [], title="Some meaningful title"
        )
        testuser = self.portal.portal_membership.getMemberById("testuser")
        testuser.setMemberProperties(dict(email="testuser@plone.org"))
        nonasciiuser = self.portal.portal_membership.getMemberById("nonasciiuser")
        nonasciiuser.setMemberProperties(dict(fullname="\xc4\xdc\xdf"))
        login(self.portal, "manager")

    def test_group_name_links_to_prefs_for_admin(self):
        """Make sure that for admins  group name links to group prefs"""
        self.request.form["search_term"] = "testgroup"
        view = getMultiAdapter((self.portal, self.request), name="sharing")
        self.assertIn(
            '<a href="http://nohost/plone/@@usergroup-groupmembership?groupname=testgroup" >',
            view(),
            msg="Group name was not linked to group prefs.",
        )

    def test_group_name_links_not_include_authusers(self):
        """Make sure that for admins  group name links to group prefs"""
        self.request.form["search_term"] = "testgroup"
        view = getMultiAdapter((self.portal, self.request), name="sharing")
        self.assertNotIn(
            '<a href="http://nohost/plone/@@usergroup-groupmembership?'
            'groupname=AuthenticatedUsers">',
            view(),
            msg="AuthenticatedUsers was linked to group prefs.",
        )

    def test_group_name_doesnt_link_to_prefs_for_reviewer(self):
        """Make sure that for admins  group name links to group prefs"""
        login(self.portal, "testreviewer")
        self.request.form["search_term"] = "testgroup"
        view = getMultiAdapter((self.portal, self.request), name="sharing")
        self.assertNotIn(
            '<a href="http://nohost/plone/@@usergroup-groupmembership?'
            'groupname=testgroup">',
            view(),
            msg="Group name link was unexpectedly shown to reviewer.",
        )
