from zope.component.testing import setUp
from zope.component.testing import tearDown

import doctest
import unittest


def test_suite():
    return unittest.TestSuite(
        doctest.DocTestSuite(
            "plone.app.i18n.locales.browser.selector",
            setUp=setUp(),
            tearDown=tearDown,
            optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
        )
    )
