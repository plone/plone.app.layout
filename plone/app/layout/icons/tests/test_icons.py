from Products.CMFPlone.utils import getToolByName
from plone.app.layout.icons.tests.base import IconsTestCase
from zope.component import getMultiAdapter
import unittest

class TestIconsView(IconsTestCase):
    """
    Test the icon multiadapter.
    """
    
    def test_actions(self):        
        self.folder.invokeFactory('Document', 'd1')
        brain = self.portal.portal_catalog(id='d1')[0]
        icon = getMultiAdapter((self.folder.d1, self.app.REQUEST, brain))        
        self.loginAsPortalOwner()
        self.portal.portal_types.manage_renameObject('Document','FakeDocument')
        self.assertEqual(icon.description, None)
        self.portal.portal_types.manage_renameObject('FakeDocument','Document')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestIconsView))
    return suite
