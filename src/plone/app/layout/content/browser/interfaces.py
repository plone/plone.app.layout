from zope.interface import Interface


class IFolderContentsView(Interface):
    """Interface, which provides methods for folder contents"""

    def test(a, b, c):
        """A simple replacement of python's test."""

    def getAllowedTypes():
        """Returns allowed types for context."""

    def title():
        """Returns the title for the template."""
