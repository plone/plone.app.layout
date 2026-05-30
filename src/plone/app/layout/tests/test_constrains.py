from plone.app.layout.content.browser.constraintypes import IConstrainForm
from zope.interface.exceptions import Invalid

import unittest


class DocumentIntegrationTest(unittest.TestCase):
    def test_formschemainvariants(self):
        class Data:
            allowed_types = []
            secondary_types = []

        bad = Data()
        bad.allowed_types = []
        bad.secondary_types = ["1"]
        good = Data()
        good.allowed_types = ["1"]
        good.secondary_types = []
        self.assertTrue(IConstrainForm.validateInvariants(good) is None)
        self.assertRaises(Invalid, IConstrainForm.validateInvariants, bad)
