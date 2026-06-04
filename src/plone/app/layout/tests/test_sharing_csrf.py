from plone.app.layout.testing import PLONE_APP_LAYOUT_FUNCTIONAL_TESTING
from plone.testing import layered

import doctest
import unittest

OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(
        layered(
            doctest.DocFileSuite(
                "sharing_csrf.txt",
                optionflags=OPTIONFLAGS,
                package="plone.app.layout.tests",
            ),
            layer=PLONE_APP_LAYOUT_FUNCTIONAL_TESTING,
        )
    )
    return suite
