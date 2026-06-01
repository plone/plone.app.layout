from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.app.layout.content.browser.file import TUS_ENABLED
from plone.app.layout.content.browser.interfaces import IFolderContentsView
from plone.app.content.interfaces import IStructureAction
from plone.app.content.utils import json_dumps
from plone.app.content.utils import json_loads
from plone.app.uuid.utils import uuidToCatalogBrain
from plone.base import PloneMessageFactory as _
from plone.base import utils
from plone.base.interfaces.controlpanel import ISiteSchema
from plone.protect.postonly import check as checkpost
from plone.registry.interfaces import IRegistry
from plone.uuid.interfaces import IUUID
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.PortalTransforms.transforms.safe_html import SafeHTML
from zope.browsermenu.interfaces import IBrowserMenu
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory


class ContentsBaseAction(BrowserView):
    success_msg = _("Success")
    failure_msg = _("Failure")
    required_obj_permission = None

    @property
    def site(self):
        return utils.get_top_site_from_url(self.context, self.request)

    def objectTitle(self, obj):
        context = aq_inner(obj)
        title = utils.pretty_title_or_id(context, context)
        return utils.safe_text(title)

    def protect(self):
        authenticator = getMultiAdapter(
            (self.context, self.request), name="authenticator"
        )
        if not authenticator.verify():
            raise Unauthorized
        checkpost(self.request)

    def json(self, data):
        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        return json_dumps(data)

    def get_selection(self):
        selection = self.request.form.get("selection", "[]")
        return json_loads(selection)

    def action(self, obj):
        """
        fill in this method to do action against each item in the selection
        """
        pass

    def finish(self):
        pass

    def __call__(self, keep_selection_order=False):
        self.protect()
        self.errors = []
        context = aq_inner(self.context)
        selection = self.get_selection()

        parts = str(self.request.form.get("folder", "").lstrip("/")).split("/")
        if parts:
            parent = self.site.unrestrictedTraverse("/".join(parts[:-1]))
            self.dest = parent.restrictedTraverse(parts[-1])

        self.catalog = getToolByName(context, "portal_catalog")
        self.mtool = getToolByName(self.context, "portal_membership")

        brains = []
        if keep_selection_order:
            brains = [uuidToCatalogBrain(uid) for uid in selection]
        else:
            brains = self.catalog(UID=selection, show_inactive=True)

        for brain in brains:
            if not brain:
                continue
            # remove everyone so we know if we missed any
            selection.remove(brain.UID)
            obj = brain.getObject()
            if self.required_obj_permission and not self.mtool.checkPermission(
                self.required_obj_permission, obj
            ):
                self.errors.append(
                    _(
                        'Permission denied for "${title}"',
                        mapping={"title": self.objectTitle(obj)},
                    )
                )
                continue
            self.action(obj)

        self.finish()
        return self.message(selection)

    def message(self, missing=[]):
        if len(missing) > 0:
            self.errors.append(
                _("${items} could not be found", mapping={"items": str(len(missing))})
            )
        if self.errors:
            msg = self.failure_msg
        else:
            msg = self.success_msg

        translated_msg = translate(msg, context=self.request)
        if self.errors:
            translated_errors = [
                translate(error, context=self.request) for error in self.errors
            ]
            translated_msg = "{:s}: {:s}".format(
                translated_msg, "\n".join(translated_errors)
            )

        return self.json(
            {"status": "warning" if self.errors else "success", "msg": translated_msg}
        )


@implementer(IFolderContentsView)
class FolderContentsView(BrowserView):
    def get_actions(self):
        actions = []
        for name, Utility in getUtilitiesFor(IStructureAction):
            utility = Utility(self.context, self.request)
            actions.append(utility)
        actions.sort(key=lambda a: a.order)
        return [a.get_options() for a in actions]

    @property
    def ignored_columns(self):
        """Return columns, which should be ignored in folder contents."""
        # These columns either have alternatives or are probably not useful
        ignored = [
            "Date",
            "Title",
            "author_name",
            "cmf_uid",
            "commentators",
            "created",
            "effective",
            "expires",
            "getIcon",
            "getMimeIcon",
            "getId",
            "getRemoteUrl",
            "in_response_to",
            "listCreators",
            "meta_type",
            "modified",
            "portal_type",
            "sync_uid",
        ]
        return ignored

    def get_columns(self):
        columns = {}
        voc = getUtility(IVocabularyFactory, "plone.app.vocabularies.MetadataFields")(
            self.context
        )
        for term in voc:
            if term.value not in self.ignored_columns:
                columns[term.value] = translate(term.title, context=self.request)

        return columns

    def get_thumb_scale(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        if settings.no_thumbs_tables:
            # thumbs to be suppressed
            return None
        thumb_scale_table = settings.thumb_scale_table
        return thumb_scale_table

    def default_page_types(self):
        registry = getUtility(IRegistry)
        return registry.get("plone.default_page_types", [])

    @property
    def ignored_indexes(self):
        ignored = [
            "Date",
            "Description",
            "Title",
            "allowedRolesAndUsers",
            "author_name",
            "cmf_uid",
            "commentators",
            "effectiveRange",
            "getId",
            "getObjectPositionInParent",
            "getRawRelatedItems",
            "in_reply_to",
            "meta_type",
            "object_provides",
            "portal_type",
            "SearchableText",
            "sync_uid",
        ]
        return ignored

    def get_indexes(self):
        # Base set of indexes
        indexes = {
            "created": translate(_("Created on"), context=self.request),
            "Creator": translate(_("Creator"), context=self.request),
            "effective": translate(_("Publication date"), context=self.request),  # noqa
            "end": translate(_("End Date"), context=self.request),
            "expires": translate(_("Expiration date"), context=self.request),
            "id": translate(_("ID"), context=self.request),
            "is_folderish": translate(_("Folder"), context=self.request),
            "modified": translate(_("Last modified"), context=self.request),  # noqa
            "review_state": translate(_("Review state"), context=self.request),
            "sortable_title": translate(_("Title"), context=self.request),
            "start": translate(_("Start Date"), context=self.request),
            "Subject": translate(_("Tags"), context=self.request),
            "total_comments": translate(
                _("Total comments"), context=self.request
            ),  # noqa
            "Type": translate(_("Type"), context=self.request),
        }
        # Filter out ignored
        indexes = {k: v for k, v in indexes.items() if k not in self.ignored_indexes}
        # Add in extra metadata indexes
        catalog = getToolByName(self.context, "portal_catalog")
        cat_indexes = [idx for idx in catalog.indexes()]
        for index in cat_indexes:
            if index not in indexes and index not in self.ignored_indexes:
                indexes[index] = translate(_(index), context=self.request)
        return indexes

    def get_options(self):
        site = utils.get_top_site_from_url(self.context, self.request)
        base_url = site.absolute_url()
        base_vocabulary = "%s/@@getVocabulary?name=" % base_url
        site_path = site.getPhysicalPath()
        context_path = self.context.getPhysicalPath()
        columns = self.get_columns()
        options = {
            "vocabularyUrl": "%splone.app.vocabularies.Catalog" % (base_vocabulary),
            "urlStructure": {"base": base_url, "appended": "/folder_contents"},
            "moveUrl": "%s{path}/fc-itemOrder" % base_url,
            "indexOptionsUrl": "%s/@@qsOptions" % base_url,
            "contextInfoUrl": "%s{path}/@@fc-contextInfo" % base_url,
            "setDefaultPageUrl": "%s{path}/@@fc-setDefaultPage" % base_url,
            "defaultPageTypes": self.default_page_types(),
            "searchParam": "Title",
            "availableColumns": columns,
            "attributes": [
                "Title",
                "path",
                "getURL",
                "getIcon",
                "getMimeIcon",
                "portal_type",
            ]
            + list(columns.keys()),  # noqa
            "buttons": self.get_actions(),
            "rearrange": {
                "properties": self.get_indexes(),
                "url": "%s{path}/@@fc-rearrange" % base_url,
            },
            "basePath": "/" + "/".join(context_path[len(site_path) :]),
            "upload": {
                "relativePath": "@@fileUpload",
                "baseUrl": base_url,
                "initialFolder": IUUID(self.context, None),
                "useTus": TUS_ENABLED,
            },
            "thumb_scale": self.get_thumb_scale(),
        }
        return options

    def __call__(self):
        self.options = json_dumps(self.get_options())
        return super().__call__()


class ContextInfo(BrowserView):
    attributes = [
        "CreationDate",
        "Creator",
        "Description",
        "EffectiveDate",
        "end",
        "exclude_from_nav",
        "getObjSize",
        "getURL",
        "id",
        "is_folderish",
        "last_comment_date",
        "location",
        "ModificationDate",
        "path",
        "portal_type",
        "review_state",
        "start",
        "Subject",
        "Title",
        "total_comments",
        "Type",
        "UID",
    ]

    def __call__(self):
        factories_menu = getUtility(
            IBrowserMenu, name="plone_contentmenu_factory", context=self.context
        ).getMenuItems(self.context, self.request)
        factories = []
        for item in factories_menu:
            if item.get("title") == "folder_add_settings":
                continue
            title = item.get("title", "")
            factories.append(
                {
                    "id": item.get("id"),
                    "title": title
                    and translate(title, context=self.request)
                    or "",  # noqa
                    "action": item.get("action"),
                }
            )

        context = aq_inner(self.context)
        transform = SafeHTML()
        crumbs = []
        top_site = utils.get_top_site_from_url(self.context, self.request)
        while not context == top_site:
            crumbs.append(
                {
                    "id": context.getId(),
                    "title": transform.scrub_html(
                        utils.pretty_title_or_id(context, context)
                    ),
                }
            )
            context = aq_parent(aq_inner(context))

        catalog = getToolByName(self.context, "portal_catalog")
        try:
            brains = catalog(UID=IUUID(self.context), show_inactive=True)
        except TypeError:
            brains = []
        item = None
        if len(brains) > 0:
            obj = brains[0]
            # context here should be site root
            base_path = "/".join(context.getPhysicalPath())
            item = {}
            for attr in self.attributes:
                key = attr
                if key == "path":
                    attr = "getPath"
                val = getattr(obj, attr, None)
                if callable(val):
                    val = val()
                if key == "path":
                    val = val[len(base_path) :]
                if isinstance(val, (bytes, str)):
                    val = transform.scrub_html(val)
                item[key] = val

        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        return json_dumps(
            {
                "addButtons": factories,
                "defaultPage": self.context.getDefaultPage(),
                "breadcrumbs": [c for c in reversed(crumbs)],
                "object": item,
            }
        )
