import unittest
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from plone.app.layout.viewlets.tests.base import ViewletsTestCase
from plone.app.layout.viewlets.comments import CommentsViewlet

class TestCommentsViewletView(ViewletsTestCase):
    """
    Test the comments viewlet
    """

    def test_time_render(self):
        request = self.app.REQUEST
        self.setRoles(['Manager', 'Member'])
        self.portal.invokeFactory('Document', 'd1')
        context = getattr(self.portal, 'd1')
        context.allowDiscussion(True)
        dtool = getToolByName(context, 'portal_discussion')
        tb = dtool.getDiscussionFor(context)
        reply_id = tb.createReply(title='Subject', text='Reply text', Creator='tester')

        viewlet = CommentsViewlet(context, request, None, None)
        viewlet.update()
        time = DateTime('2009/10/20 15:00')
        self.assertEqual(viewlet.format_time(time), 'Oct 20, 2009 03:00 PM')
        
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCommentsViewletView))
    return suite
