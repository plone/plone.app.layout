from plone.app.layout.testing import FUNCTIONAL_TESTING
from zExceptions import Forbidden
from zope.component import getMultiAdapter

import unittest


class TestAttackVector(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def test_regression(self):
        portal = self.layer["portal"]
        request = self.layer["request"]
        view = getMultiAdapter((portal, request), name="confirm-action")
        request.form.update({"original_url": "foobar"})
        self.assertTrue('value="foobar"' in view())

    def test_valid_url(self):
        portal = self.layer["portal"]
        request = self.layer["request"]
        view = getMultiAdapter((portal, request), name="confirm-action")
        request.form.update({"original_url": "javascript:alert(1)"})
        self.assertRaises(Forbidden, view)
