from zope.component.testing import setUp
from zope.component.testing import tearDown

import doctest
import unittest


def test_suite():
    return unittest.TestSuite(
        doctest.DocFileSuite(
            "table.txt",
            package="plone.app.layout.content.browser",
            optionflags=doctest.ELLIPSIS,
            setUp=setUp,
            tearDown=tearDown,
        )
    )
