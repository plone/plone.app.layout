import unittest2 as unittest
from plone.app.layout.testing import INTEGRATION_TESTING
from plone.app.layout.viewlets.content import ContentRelatedItems
from plone.app.relationfield.behavior import IRelatedItems
from plone.app.testing import TEST_USER_ID, setRoles
from plone.dexterity.fti import DexterityFTI
from z3c.form.interfaces import IDataManager
from zope.component import getMultiAdapter
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class TestRealtionFieldViewlet(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.invokeFactory('Folder', 'test-folder')
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        self.folder = self.portal['test-folder']

        # to use behaviors we need a dexterity fti
        fti = DexterityFTI('TestContent')
        self.portal.portal_types._setObject('TestContent', fti)
        fti.klass = 'plone.dexterity.content.Item'
        fti.filter_content_types = False
        fti.behaviors = ('plone.app.dexterity.behaviors.metadata.IBasic',
                         'plone.app.relationfield.behavior.IRelatedItems')

        doc1 = self.folder.invokeFactory('TestContent', 'doc1',
                                         title='Document 1')
        doc1 = self.folder[doc1]
        self.folder.invokeFactory('TestContent', 'doc2', title='Document 2', )
        self.folder.invokeFactory('TestContent', 'doc3', title='Document 3', )
        dm = getMultiAdapter((doc1, IRelatedItems['relatedItems']),
                             IDataManager)
        dm.set([self.folder['doc2'], self.folder['doc3']])
        notify(ObjectModifiedEvent(doc1))

    def testRelation(self):
        request = self.layer['request']
        viewlet = ContentRelatedItems(self.folder['doc1'], request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.Title for x in related],
                         ['Document 2', 'Document 3'])

    def testBrokenRelation(self):
        del self.folder['doc3']
        request = self.layer['request']
        viewlet = ContentRelatedItems(self.folder['doc1'], request, None, None)
        viewlet.update()
        related = viewlet.related_items()
        self.assertEqual([x.Title for x in related],
                         ['Document 2'])


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
