from plone.app.layout.content.browser import vocabulary
from plone.app.layout.content.browser.file import FileUploadView
from plone.app.layout.content.browser.query import QueryStringIndexOptions
from plone.app.layout.content.browser.vocabulary import VocabularyView
from plone.app.content.testing import ExampleFunctionVocabulary
from plone.app.content.testing import ExampleVocabulary
from plone.app.content.testing import PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING
from plone.app.content.testing import PLONE_APP_CONTENT_DX_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.app.z3cform.interfaces import IFieldPermissionChecker
from Products.CMFCore.indexing import processQueue
from unittest import mock
from zope.component import getMultiAdapter
from zope.component import provideAdapter
from zope.component import provideUtility
from zope.component.globalregistry import base
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import noLongerProvides
from zope.publisher.browser import TestRequest

import json
import operator
import os
import transaction
import unittest

_dir = os.path.dirname(__file__)


class PermissionChecker:
    def __init__(self, context):
        pass

    def validate(self, field_name, vocabulary_name=None):
        if field_name == "allowed_field":
            return True
        elif field_name == "disallowed_field":
            return False
        else:
            raise AttributeError("Missing Field")


class ICustomPermissionProvider(Interface):
    pass


def _enable_permission_checker(context):
    provideAdapter(
        PermissionChecker,
        adapts=(ICustomPermissionProvider,),
        provides=IFieldPermissionChecker,
    )
    alsoProvides(context, ICustomPermissionProvider)


def _disable_permission_checker(context):
    noLongerProvides(context, ICustomPermissionProvider)
    base.unregisterAdapter(
        required=(ICustomPermissionProvider,), provided=IFieldPermissionChecker
    )


class BrowserTest(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_INTEGRATION_TESTING

    def setUp(self):
        self.request = TestRequest(environ={"HTTP_ACCEPT_LANGUAGE": "en"})
        setRequest(self.request)
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        provideUtility(ExampleVocabulary(), name="vocab_class")
        provideUtility(ExampleFunctionVocabulary, name="vocab_function")
        vocabulary.PERMISSIONS.update(
            {
                "vocab_class": "Modify portal content",
                "vocab_function": "Modify portal content",
            }
        )

    def testVocabularyQueryString(self):
        """Test querying a class based vocabulary with a search string."""
        view = VocabularyView(self.portal, self.request)
        self.request.form.update({"name": "vocab_class", "query": "three"})
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)

    def testVocabularyFunctionQueryString(self):
        """Test querying a function based vocabulary with a search string."""
        view = VocabularyView(self.portal, self.request)
        self.request.form.update({"name": "vocab_function", "query": "third"})
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)

    def testVocabularyNoResults(self):
        """Tests that the widgets displays correctly"""
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/foo",
                }
            ]
        }
        self.request.form.update(
            {"name": "plone.app.vocabularies.Catalog", "query": json.dumps(query)}
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 0)

    def testVocabularyCatalogResults(self):
        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/plone",
                },
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": "Document",
                },
            ]
        }
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "query": json.dumps(query),
                "attributes": ["UID", "id", "title", "path"],
            }
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)

    def testVocabularyCatalogUnsafeMetadataAllowed(self):
        """Users with permission "Modify portal content" are allowed to see
        ``_unsafe_metadata``.
        """
        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/plone/page",
                }
            ]
        }
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "query": json.dumps(query),
                "attributes": [
                    "id",
                    "commentors",
                    "Creator",
                    "listCreators",
                ],
            }
        )
        data = json.loads(view())
        self.assertEqual(len(list(data["results"][0].keys())), 4)

    def testVocabularyCatalogUnsafeMetadataDisallowed(self):
        """Users without permission "Modify portal content" are not allowed to
        see ``_unsafe_metadata``.
        """
        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()
        # Downgrade permissions
        setRoles(self.portal, TEST_USER_ID, [])
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/plone/page",
                }
            ]
        }
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "query": json.dumps(query),
                "attributes": [
                    "id",
                    "commentors",
                    "Creator",
                    "listCreators",
                ],
            }
        )
        data = json.loads(view())
        # Only one result key should be returned, as ``commentors``,
        # ``Creator`` and ``listCreators`` is considered unsafe and thus
        # skipped.
        self.assertEqual(len(list(data["results"][0].keys())), 1)

    def testVocabularyBatching(self):
        amount = 30
        for i in range(amount):
            self.portal.invokeFactory(
                "Document", id="page" + str(i), title="Page" + str(i)
            )
            self.portal["page" + str(i)].reindexObject()
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/plone",
                },
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": "Document",
                },
            ]
        }
        # batch pages are 1-based
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "query": json.dumps(query),
                "attributes": ["UID", "id", "title", "path"],
                "batch": {"page": "1", "size": "10"},
            }
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["total"], amount)

    def testVocabularyEncoding(self):
        """The vocabulary should not return the binary encoded token
        ("N=C3=A5=C3=B8=C3=AF"), but instead the value as the id in the result
        set. Fixes an encoding problem. See:
        https://github.com/plone/Products.CMFPlone/issues/650
        """
        test_val = "Nåøï"

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.subject = (test_val,)
        self.portal.page.reindexObject(idxs=["Subject"])
        processQueue()

        self.request.form["name"] = "plone.app.vocabularies.Keywords"
        results = getMultiAdapter((self.portal, self.request), name="getVocabulary")()
        results = json.loads(results)
        result = results["results"][0]

        self.assertEqual(result["text"], test_val)
        self.assertEqual(result["id"], test_val)

    def testVocabularyHtmlEntity(self):
        """The vocabulary token should not convert to htmlentities.
        See https://github.com/plone/Products.CMFPlone/issues/3874
        """
        test_val = "Question & Answer"

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.subject = (test_val,)
        self.portal.page.reindexObject(idxs=["Subject"])
        processQueue()

        self.request.form["name"] = "plone.app.vocabularies.Keywords"
        results = getMultiAdapter((self.portal, self.request), name="getVocabulary")()
        results = json.loads(results)
        result = results["results"][0]

        self.assertEqual(result["text"], test_val)
        self.assertEqual(result["id"], test_val)

    def testVocabularyUnauthorized(self):
        setRoles(self.portal, TEST_USER_ID, [])
        view = VocabularyView(self.portal, self.request)
        self.request.form.update(
            {"name": "plone.app.vocabularies.Users", "query": TEST_USER_NAME}
        )
        data = json.loads(view())
        self.assertEqual(data["error"], "Vocabulary lookup not allowed")

    def testVocabularyMissing(self):
        view = VocabularyView(self.portal, self.request)
        self.request.form.update(
            {
                "name": "vocabulary.that.does.not.exist",
            }
        )
        data = json.loads(view())
        self.assertEqual(data["error"], "Vocabulary lookup not allowed")

    def testPermissionCheckerAllowed(self):
        # Setup a custom permission checker on the portal
        _enable_permission_checker(self.portal)
        view = VocabularyView(self.portal, self.request)

        # Allowed field is allowed
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.PortalTypes",
                "field": "allowed_field",
            }
        )
        data = json.loads(view())
        self.assertEqual(
            len(data["results"]), len(self.portal.portal_types.objectIds())
        )
        _disable_permission_checker(self.portal)

    def testPermissionCheckerUnknownVocab(self):
        _enable_permission_checker(self.portal)
        view = VocabularyView(self.portal, self.request)
        # Unknown vocabulary gives error
        self.request.form.update(
            {
                "name": "vocab.does.not.exist",
                "field": "allowed_field",
            }
        )
        data = json.loads(view())
        self.assertEqual(
            data["error"],
            'No factory with name "{}" exists.'.format("vocab.does.not.exist"),
        )
        _disable_permission_checker(self.portal)

    def testPermissionCheckerDisallowed(self):
        _enable_permission_checker(self.portal)
        view = VocabularyView(self.portal, self.request)
        # Disallowed field is not allowed
        # Allowed field is allowed
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.PortalTypes",
                "field": "disallowed_field",
            }
        )
        data = json.loads(view())
        self.assertEqual(data["error"], "Vocabulary lookup not allowed")
        _disable_permission_checker(self.portal)

    def testPermissionCheckerShortCircuit(self):
        _enable_permission_checker(self.portal)
        view = VocabularyView(self.portal, self.request)
        # Known vocabulary name short-circuits field permission check
        # global permission
        self.request.form["name"] = "plone.app.vocabularies.Users"
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Users",
                "field": "disallowed_field",
            }
        )
        data = json.loads(view())
        self.assertEqual(data["results"], [])
        _disable_permission_checker(self.portal)

    def testPermissionCheckerUnknownField(self):
        _enable_permission_checker(self.portal)
        view = VocabularyView(self.portal, self.request)
        # Unknown field is raises error
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.PortalTypes",
                "field": "missing_field",
            }
        )
        with self.assertRaises(AttributeError):
            view()
        _disable_permission_checker(self.portal)

    def testVocabularyUsers(self):
        acl_users = self.portal.acl_users
        membership = self.portal.portal_membership
        amount = 10
        # Let's test that safe html is used on the fullname,
        # as alternative to the workaround in PloneHotfix20210518.
        for i in range(amount):
            id = "user" + str(i)
            acl_users.userFolderAddUser(id, TEST_USER_PASSWORD, ["Member"], [])
            member = membership.getMemberById(id)
            # Make user0 the hacker.
            if i == 0:
                fullname = "user <script>alert('tag')</script> hacker"
            else:
                fullname = id
            member.setMemberProperties(mapping={"fullname": fullname})
        view = VocabularyView(self.portal, self.request)
        self.request.form.update(
            {"name": "plone.app.vocabularies.Users", "query": "user"}
        )
        data = json.loads(view())

        self.assertEqual(len(data["results"]), amount)
        # Let's sort, just to be sure.
        results = sorted(data["results"], key=operator.itemgetter("id"))
        # The first one is the hacker.  The hack should have failed.
        self.assertDictEqual(results[0], {"id": "user0", "text": "user  hacker"})

    def testSource(self):
        from z3c.form.browser.text import TextWidget
        from zope.interface import implementer
        from zope.interface import Interface
        from zope.schema import Choice
        from zope.schema.interfaces import ISource

        @implementer(ISource)
        class DummyCatalogSource:
            def search_catalog(self, query):
                querytext = query["SearchableText"]["query"]
                return [mock.Mock(id=querytext)]

        widget = TextWidget(self.request)
        widget.context = self.portal
        widget.field = Choice(source=DummyCatalogSource())
        widget.field.interface = Interface

        from plone.app.layout.content.browser.vocabulary import SourceView

        view = SourceView(widget, self.request)
        query = {
            "criteria": [
                {
                    "i": "SearchableText",
                    "o": "plone.app.querystring.operation.string.is",
                    "v": "foo",
                }
            ]
        }
        self.request.form.update(
            {
                "query": json.dumps(query),
                "attributes": "id",
            }
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["id"], "foo")

    def testSourceCollectionField(self):
        # This test uses a collection field
        # and a source providing the 'search' method
        # to help achieve coverage.
        from z3c.form.browser.text import TextWidget
        from zope.interface import implementer
        from zope.interface import Interface
        from zope.schema import Choice
        from zope.schema import List
        from zope.schema.interfaces import ISource
        from zope.schema.vocabulary import SimpleTerm

        @implementer(ISource)
        class DummySource:
            def search(self, query):
                terms = [SimpleTerm(query, query)]
                return iter(terms)

        widget = TextWidget(self.request)
        widget.context = self.portal
        widget.field = List(value_type=Choice(source=DummySource()))
        widget.field.interface = Interface

        from plone.app.layout.content.browser.vocabulary import SourceView

        view = SourceView(widget, self.request)
        query = {
            "criteria": [
                {
                    "i": "SearchableText",
                    "o": "plone.app.querystring.operation.string.is",
                    "v": "foo",
                }
            ],
            "sort_on": "id",
            "sort_order": "ascending",
        }
        self.request.form.update(
            {
                "query": json.dumps(query),
                "batch": json.dumps({"size": 10, "page": 1}),
            }
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["id"], "foo")

    def testSourcePermissionDenied(self):
        from z3c.form.browser.text import TextWidget
        from zope.interface import implementer
        from zope.interface import Interface
        from zope.schema import Choice
        from zope.schema.interfaces import ISource

        @implementer(ISource)
        class DummyCatalogSource:
            def search_catalog(self, query):
                querytext = query["SearchableText"]["query"]
                return [mock.Mock(id=querytext)]

        widget = TextWidget(self.request)
        widget.context = self.portal
        widget.field = Choice(source=DummyCatalogSource())
        widget.field.interface = Interface

        from plone.app.layout.content.browser.vocabulary import SourceView

        view = SourceView(widget, self.request)
        query = {
            "criteria": [
                {
                    "i": "SearchableText",
                    "o": "plone.app.querystring.operation.string.is",
                    "v": "foo",
                }
            ]
        }
        self.request.form.update(
            {
                "query": json.dumps(query),
            }
        )
        logout()
        data = json.loads(view())
        self.assertEqual(data["error"], "Vocabulary lookup not allowed.")

    def testSourceDefaultPermission(self):
        from plone.app.layout.content.browser.vocabulary import SourceView
        from z3c.form.browser.text import TextWidget

        widget = TextWidget(self.request)
        view = SourceView(widget, self.request)
        self.assertEqual(view.default_permission, "cmf.ModifyPortalContent")

    def testSourceDefaultPermissionOnAddForm(self):
        from plone.app.layout.content.browser.vocabulary import SourceView
        from z3c.form import form
        from z3c.form.browser.text import TextWidget

        widget = TextWidget(self.request)
        widget.form = form.AddForm(self.portal, self.request)

        view = SourceView(widget, self.request)
        self.assertEqual(view.default_permission, "cmf.AddPortalContent")

    def testSourceTextQuery(self):
        from z3c.form.browser.text import TextWidget
        from zope.interface import implementer
        from zope.interface import Interface
        from zope.schema import Choice
        from zope.schema.interfaces import ISource

        @implementer(ISource)
        class DummyCatalogSource:
            def search(self, query):
                return [mock.Mock(value=mock.Mock(id=query))]

        widget = TextWidget(self.request)
        widget.context = self.portal
        widget.field = Choice(source=DummyCatalogSource())
        widget.field.interface = Interface

        from plone.app.layout.content.browser.vocabulary import SourceView

        view = SourceView(widget, self.request)
        self.request.form.update(
            {
                "query": "foo",
                "attributes": "id",
            }
        )
        data = json.loads(view())
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["id"], "foo")

    def testQueryStringConfiguration(self):
        view = QueryStringIndexOptions(self.portal, self.request)
        data = json.loads(view())
        # just test one so we know it's working...
        self.assertEqual(data["indexes"]["sortable_title"]["sortable"], True)

    @mock.patch("zope.i18n.negotiate", new=lambda ctx: "de")
    def testUntranslatableMetadata(self):
        """Test translation of ``@@getVocabulary`` view results.
        From the standard metadata columns, only ``Type`` is translated.
        """
        # Language is set via language negotiaton patch.

        self.portal.invokeFactory("Document", id="page", title="page")
        self.portal.page.reindexObject()
        view = VocabularyView(self.portal, self.request)
        query = {
            "criteria": [
                {
                    "i": "path",
                    "o": "plone.app.querystring.operation.string.path",
                    "v": "/plone/page",
                }
            ]
        }
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "query": json.dumps(query),
                "attributes": [
                    "id",
                    "portal_type",
                    "Type",
                ],
            }
        )

        # data['results'] should return one item, which represents the document
        # created before.
        data = json.loads(view())

        # Type is translated
        self.assertEqual(data["results"][0]["Type"], "Seite")

        # portal_type is never translated
        self.assertEqual(data["results"][0]["portal_type"], "Document")

    def testGetMimeIcon(self):
        """Check if the returned icon is correct"""
        query = {
            "criteria": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": "File",
                },
            ]
        }
        self.request.form.update(
            {
                "name": "plone.app.vocabularies.Catalog",
                "attributes": ["getMimeIcon"],
                "query": json.dumps(query),
            }
        )
        view = VocabularyView(self.portal, self.request)

        # Check an empty file
        self.portal.invokeFactory("File", id="my-file", title="My file")
        obj = self.portal["my-file"]
        obj.reindexObject()

        self.assertListEqual(json.loads(view())["results"], [{"getMimeIcon": None}])

        # mock a pdf
        obj.file = mock.Mock(contentType="application/pdf")
        obj.reindexObject()
        self.assertListEqual(
            json.loads(view())["results"],
            [{"getMimeIcon": "/plone/++resource++mimetype.icons/pdf.png"}],
        )

        # mock something unknown
        obj.file = mock.Mock(contentType="x-foo/x-bar")
        obj.reindexObject()
        self.assertListEqual(
            json.loads(view())["results"],
            [{"getMimeIcon": "/plone/++resource++mimetype.icons/unknown.png"}],
        )

    def testGeneratesValidJson(self):
        from zope.schema.vocabulary import SimpleTerm
        from zope.schema.vocabulary import SimpleVocabulary

        view = VocabularyView(self.portal, self.request)
        vocab = SimpleVocabulary(
            [
                SimpleTerm(
                    token=f"term {idx} <b>",
                    value=f"term {idx} <b>",
                    title=f"term {idx} <b>",
                )
                for idx in range(3)
            ]
        )
        with mock.patch.object(view, "get_vocabulary", return_value=vocab):
            result = view()
        # The above values could result in invalid json if there is an error in
        # the code: the following call would give a json.decoder.JSONDecodeError.
        # See https://github.com/plone/plone.app.content/pull/288
        parsed = json.loads(result)
        self.assertEqual(parsed["results"][0]["text"], "term 0 <b></b>")


class FunctionalBrowserTest(unittest.TestCase):
    layer = PLONE_APP_CONTENT_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.request = TestRequest()
        setRequest(self.request)
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def testFileUpload(self):
        view = FileUploadView(self.portal, self.request)
        from plone.namedfile.file import FileChunk

        chunk = FileChunk(b"foobar")
        chunk.filename = "test.xml"
        self.request.form["file"] = chunk
        self.request.REQUEST_METHOD = "POST"
        # the next calls plone.app.dexterity.factories and does a
        # transaction.commit. Needs cleanup and FunctionalTesting layer.
        data = json.loads(view())
        self.assertEqual(data["url"], "http://nohost/plone/test.xml")
        self.assertTrue(data["UID"] is not None)
        # clean it up...
        self.portal.manage_delObjects(["test.xml"])
        transaction.commit()

    def testFileUploadTxt(self):
        view = FileUploadView(self.portal, self.request)
        from plone.namedfile.file import FileChunk

        chunk = FileChunk(b"foobar")
        chunk.filename = "test.txt"
        self.request.form["file"] = chunk
        self.request.REQUEST_METHOD = "POST"
        # the next calls plone.app.dexterity.factories and does a
        # transaction.commit. Needs cleanup and FunctionalTesting layer.
        data = json.loads(view())
        self.assertEqual(data["url"], "http://nohost/plone/test.txt")
        self.assertTrue(data["UID"] is not None)
        # clean it up...
        self.portal.manage_delObjects(["test.txt"])
        transaction.commit()
