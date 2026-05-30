from AccessControl import getSecurityManager
from Acquisition import aq_base
from html import unescape
from logging import getLogger
from plone.app.content.utils import json_dumps
from plone.app.content.utils import json_loads
from plone.app.querystring import queryparser
from plone.app.z3cform.interfaces import IFieldPermissionChecker
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from plone.base import PloneMessageFactory as _
from plone.base.interfaces.siteroot import INavigationRoot
from plone.base.navigationroot import get_navigation_root
from plone.base.utils import safe_text
from plone.memoize.view import memoize
from plone.supermodel.utils import mergedTaggedValueDict
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.MimetypesRegistry.MimeTypeItem import guess_icon_path
from Products.MimetypesRegistry.MimeTypeItem import PREFIX
from Products.PortalTransforms.transforms.safe_html import SafeHTML
from types import FunctionType
from z3c.form.browser.object import ObjectWidget
from z3c.form.interfaces import IAddForm
from z3c.form.interfaces import ISubForm
from zope.component import getUtility
from zope.component import queryAdapter
from zope.component import queryUtility
from zope.deprecation import deprecated
from zope.i18n import translate
from zope.schema.interfaces import ICollection
from zope.schema.interfaces import IVocabularyFactory
from zope.security.interfaces import IPermission

import inspect
import itertools

logger = getLogger(__name__)

MAX_BATCH_SIZE = 500  # prevent overloading server

DEFAULT_PERMISSION = "View"
DEFAULT_PERMISSION_SECURE = "Modify portal content"
PERMISSIONS = {
    "plone.app.vocabularies.Catalog": "View",
    "plone.app.vocabularies.Keywords": "Modify portal content",
    "plone.app.vocabularies.SyndicatableFeedItems": "Modify portal content",
    "plone.app.vocabularies.Users": "Modify portal content",
    "plone.app.multilingual.RootCatalog": "View",
}
TRANSLATED_IGNORED = [
    "author_name",
    "cmf_uid",
    "commentators",
    "created",
    "CreationDate",
    "Creator",
    "Date",
    "Description",
    "effective",
    "EffectiveDate",
    "end",
    "exclude_from_nav",
    "ExpirationDate",
    "expires",
    "getIcon",
    "getMimeIcon",
    "getId",
    "getObjSize",
    "getRemoteUrl",
    "getURL",
    "id",
    "in_response_to",
    "is_folderish",
    "last_comment_date",
    "listCreators",
    "location",
    "meta_type",
    "ModificationDate",
    "modified",
    "path",
    "portal_type",
    "review_state",
    "start",
    "Subject",
    "sync_uid",
    "Title",
    "total_comments",
    "UID",
]

_permissions = PERMISSIONS
deprecated("_permissions", "Use PERMISSIONS variable instead.")


def _parseJSON(s):
    # XXX this should be changed to a try loads except return s
    if isinstance(s, str):
        s = s.strip()
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):  # detect if json
            return json_loads(s)
    return s


_unsafe_metadata = [
    "author_name",
    "commentors",
    "Creator",
    "listCreators",
]
_safe_callable_metadata = [
    "getIcon",
    "getPath",
    "getURL",
    "is_folderish",
    "review_state",
]


class VocabLookupException(Exception):
    pass


class BaseVocabularyView(BrowserView):
    def get_translated_ignored(self):
        return TRANSLATED_IGNORED

    def get_base_path(self, context):
        return get_navigation_root(context)

    def __call__(self):
        """
        Accepts GET parameters of:
        name: Name of the vocabulary
        field: Name of the field the vocabulary is being retrieved for
        query: string or json object of criteria and options.
            json value consists of a structure:
                {
                    criteria: object,
                    sort_on: index,
                    sort_order: (asc|reversed)
                }
        attributes: comma separated, or json object list
        batch: {
            page: 1-based page of results,
            size: size of paged results
        }
        """
        context = self.get_context()
        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )

        try:
            vocabulary = self.get_vocabulary()
        except VocabLookupException as e:
            return json_dumps({"error": e.args[0]})

        results_are_brains = False
        if hasattr(vocabulary, "search_catalog"):
            query = self.parsed_query()
            results = vocabulary.search_catalog(query)
            results_are_brains = True
        elif hasattr(vocabulary, "search"):
            try:
                query = self.parsed_query()["SearchableText"]["query"]
            except KeyError:
                results = iter(vocabulary)
            else:
                results = vocabulary.search(query)
        else:
            results = vocabulary

        try:
            total = len(results)
        except TypeError:
            # do not error if object does not support __len__
            # we'll check again later if we can figure some size
            # out
            total = 0

        # get batch
        batch = _parseJSON(self.request.get("batch", ""))
        if batch and ("size" not in batch or "page" not in batch):
            batch = None  # batching not providing correct options
        if batch:
            # must be sliceable for batching support
            page = int(batch["page"])
            size = int(batch["size"])
            if size > MAX_BATCH_SIZE:
                raise Exception("Max batch size is 500")
            # page is being passed in is 1-based
            start = (max(page - 1, 0)) * size
            end = start + size
            # Try __getitem__-based slice, then iterator slice.
            # The iterator slice has to consume the iterator through
            # to the desired slice, but that shouldn't be the end
            # of the world because at some point the user will hopefully
            # give up scrolling and search instead.
            try:
                results = results[start:end]
            except TypeError:
                results = itertools.islice(results, start, end)

        # build result items
        items = []

        attributes = _parseJSON(self.request.get("attributes", ""))
        if isinstance(attributes, str) and attributes:
            attributes = attributes.split(",")

        translate_ignored = self.get_translated_ignored()
        transform = SafeHTML()
        if attributes:
            base_path = self.get_base_path(context)
            sm = getSecurityManager()
            can_edit = sm.checkPermission(DEFAULT_PERMISSION_SECURE, context)
            mtt = getToolByName(self.context, "mimetypes_registry")
            for vocab_item in results:
                if not results_are_brains:
                    vocab_item = vocab_item.value
                item = {}
                for attr in attributes:
                    key = attr
                    if ":" in attr:
                        key, attr = attr.split(":", 1)
                    if attr in _unsafe_metadata and not can_edit:
                        continue
                    if key == "path":
                        attr = "getPath"
                    val = getattr(vocab_item, attr, None)
                    if callable(val):
                        if attr in _safe_callable_metadata:
                            val = val()
                        else:
                            continue
                    if key == "path" and val is not None:
                        val = val[len(base_path) :]
                    if key not in translate_ignored and isinstance(val, str):
                        val = translate(_(safe_text(val)), context=self.request)
                    item[key] = val
                    if key == "getMimeIcon":
                        item[key] = None
                        # get mime type icon url from mimetype registry'
                        contenttype = aq_base(getattr(vocab_item, "mime_type", None))
                        if contenttype:
                            ctype = mtt.lookup(contenttype)
                            if ctype:
                                item[key] = "/".join(
                                    [base_path, guess_icon_path(ctype[0])]
                                )
                            else:
                                item[key] = "/".join(
                                    [
                                        base_path,
                                        PREFIX.rstrip("/"),
                                        "unknown.png",
                                    ]
                                )
                items.append(item)
        else:
            items = [
                {
                    "id": unescape(transform.scrub_html(item.value)),
                    "text": (
                        unescape(transform.scrub_html(item.title)) if item.title else ""
                    ),
                }
                for item in results
            ]

        if total == 0:
            total = len(items)

        return json_dumps({"results": items, "total": total})

    def parsed_query(
        self,
    ):
        query = _parseJSON(self.request.get("query", ""))
        if isinstance(query, str):
            query = {"SearchableText": {"query": query}}
        elif query:
            parsed = queryparser.parseFormquery(self.get_context(), query["criteria"])
            if "sort_on" in query:
                parsed["sort_on"] = query["sort_on"]
            if "sort_order" in query:
                parsed["sort_order"] = str(query["sort_order"])
            query = parsed
        else:
            query = {}
        return query


class VocabularyView(BaseVocabularyView):
    """Queries a named vocabulary and returns JSON-formatted results."""

    def get_context(self):
        return self.context

    def get_vocabulary(self):
        # Look up named vocabulary and check permission.

        context = self.context
        factory_name = self.request.get("name", None)
        field_name = self.request.get("field", None)
        if not factory_name:
            raise VocabLookupException("No factory provided.")
        authorized = None
        sm = getSecurityManager()
        if factory_name not in PERMISSIONS or not INavigationRoot.providedBy(context):
            # Check field specific permission
            if field_name:
                permission_checker = queryAdapter(context, IFieldPermissionChecker)
                if permission_checker is not None:
                    authorized = permission_checker.validate(field_name, factory_name)
                elif sm.checkPermission(
                    PERMISSIONS.get(factory_name, DEFAULT_PERMISSION), context
                ):
                    # If no checker, fall back to checking the global registry
                    authorized = True

            if not authorized:
                raise VocabLookupException("Vocabulary lookup not allowed")

        # Short circuit if we are on the site root and permission is
        # in global registry
        elif not sm.checkPermission(
            PERMISSIONS.get(factory_name, DEFAULT_PERMISSION), context
        ):
            raise VocabLookupException("Vocabulary lookup not allowed")

        factory = queryUtility(IVocabularyFactory, factory_name)
        if not factory:
            raise VocabLookupException(
                'No factory with name "%s" exists.' % factory_name
            )

        # This part is for backwards-compatibility with the first
        # generation of vocabularies created for plone.app.widgets,
        # which take the (unparsed) query as a parameter of the vocab
        # factory rather than as a separate search method.
        if isinstance(factory, FunctionType):
            factory_spec = inspect.getfullargspec(factory)
        else:
            factory_spec = inspect.getfullargspec(factory.__call__)
        query = _parseJSON(self.request.get("query", ""))
        if query and "query" in factory_spec.args:
            vocabulary = factory(context, query=query)
        else:
            # This is what is reached for non-legacy vocabularies.
            vocabulary = factory(context)

        return vocabulary


class SourceView(BaseVocabularyView):
    """Queries a field's source and returns JSON-formatted results."""

    def get_context(self):
        if ISubForm.providedBy(self.context.form):
            context = self.context.form.parentForm.context
        elif isinstance(self.context.form, ObjectWidget):
            context = self.context.form.form.context
        else:
            context = self.context.context
        return context

    @property
    @memoize
    def default_permission(self):
        if IAddForm.providedBy(self.context.form):
            return "cmf.AddPortalContent"
        return "cmf.ModifyPortalContent"

    def get_vocabulary(self):
        widget = self.context
        field = widget.field.bind(widget.context)

        # check field's write permission
        info = mergedTaggedValueDict(field.interface, WRITE_PERMISSIONS_KEY)
        permission_name = info.get(field.__name__, self.default_permission)
        permission = queryUtility(IPermission, name=permission_name)
        if permission is None:
            permission = getUtility(IPermission, name=self.default_permission)
        if not getSecurityManager().checkPermission(
            permission.title, self.get_context()
        ):
            raise VocabLookupException("Vocabulary lookup not allowed.")

        if ICollection.providedBy(field):
            return field.value_type.vocabulary
        return field.vocabulary
