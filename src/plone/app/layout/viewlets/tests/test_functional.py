from plone.app.layout.testing import PLONE_APP_LAYOUT_FUNCTIONAL_TESTING
from plone.testing import layered

import doctest
import unittest

optionflags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
normal_testfiles = [
    "history.txt",
]


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(
        [
            layered(
                doctest.DocFileSuite(
                    test,
                    optionflags=optionflags,
                ),
                layer=PLONE_APP_LAYOUT_FUNCTIONAL_TESTING,
            )
            for test in normal_testfiles
        ]
    )
    return suite
