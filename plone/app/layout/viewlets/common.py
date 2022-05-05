from AccessControl import getSecurityManager
from Acquisition import aq_base
from Acquisition import aq_inner
from collections import defaultdict
from functools import total_ordering
from html import escape
from plone.app.layout.globals.interfaces import IViewView
from plone.app.layout.navigation.root import getNavigationRoot
from plone.base.utils import safe_text
from plone.i18n.interfaces import ILanguageSchema
from plone.memoize.view import memoize
from plone.protect.utils import addTokenToUrl
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from plone.base.interfaces import IPloneSiteRoot
from plone.base.interfaces import ISearchSchema
from plone.base.interfaces import ISiteSchema
from plone.base.interfaces.controlpanel import INavigationSchema
from Products.CMFPlone.utils import getSiteLogo
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from urllib.parse import unquote
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet

import json
import zope.deferredimport


zope.deferredimport.initialize()
zope.deferredimport.deprecated(
    "Import from plone.app.portlets.browser.viewlets instead",
    ManagePortletsFallbackViewlet="plone.app.portlets.browser.viewlets:ManagePortletsFallbackViewlet",
    FooterViewlet="plone.app.portlets.browser.viewlets:FooterViewlet",
)


@implementer(IViewlet)
@total_ordering
class ViewletBase(BrowserView):
    """Base class with common functions for link viewlets."""

    def __init__(self, context, request, view, manager=None):
        super().__init__(context, request)
        self.__parent__ = view
        self.context = context
        self.request = request
        self.view = view
        self.manager = manager

    def __hash__(self):
        return id(self) * 16

    def update(self):
        self.portal_state = getMultiAdapter(
            (self.context, self.request), name="plone_portal_state"
        )
        self.site_url = self.portal_state.portal_url()
        self.navigation_root_url = self.portal_state.navigation_root_url()

    def render(self):
        # defer to index method, because that's what gets overridden by the
        # template ZCML attribute
        return self.index()

    def index(self):
        raise NotImplementedError("`index` method must be implemented by subclass.")

    def __lt__(self, other):
        """Sort by name"""
        return self.__name__ < other.__name__

    def __eq__(self, other):
        """Check for equality"""
        return id(self) == id(other)


class TitleViewlet(ViewletBase):
    index = ViewPageTemplateFile("title.pt")

    # seperator of page- and portal-title
    sep = " &mdash; "

    @property
    @memoize
    def site_title_setting(self):
        registry = getUtility(IRegistry)
        site_settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        return site_settings.site_title

    @property
    @memoize
    def page_title(self):
        """
        Get the page title. If we are in the portal_factory we want use the
        "Add $FTI_TITLE" form (see #12117).

        NOTE: other implementative options can be:
         - to use "Untitled" instead of "Add" or
         - to check the isTemporary method of the edit view instead of the
           creation_flag
        """
        if hasattr(aq_base(self.context), "isTemporary") and self.context.isTemporary():
            # if we are in the portal_factory we want the page title to be
            # "Add fti title"
            portal_types = getToolByName(self.context, "portal_types")
            fti = portal_types.getTypeInfo(self.context)
            return translate(
                "heading_add_item",
                domain="plone",
                mapping={"itemtype": fti.Title()},
                context=self.request,
                default="Add ${itemtype}",
            )

        # If we are on portal root, look up the portal title from registry
        if IPloneSiteRoot.providedBy(self.context):
            return self.site_title_setting

        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        return escape(safe_text(context_state.object_title()))

    def update(self):
        if IPloneSiteRoot.providedBy(self.context):
            self.site_title = self.site_title_setting
            return
        portal_state = getMultiAdapter(
            (self.context, self.request), name="plone_portal_state"
        )
        if IPloneSiteRoot.providedBy(portal_state.navigation_root()):
            portal_title = self.site_title_setting
        else:
            portal_title = escape(safe_text(portal_state.navigation_root_title()))
        if self.page_title == portal_title:
            self.site_title = portal_title
        else:
            self.site_title = self.sep.join([self.page_title, portal_title])


class DublinCoreViewlet(ViewletBase):
    index = ViewPageTemplateFile("dublin_core.pt")

    def update(self):
        plone_utils = getToolByName(self.context, "plone_utils")
        context = aq_inner(self.context)
        self.metatags = plone_utils.listMetaTags(context).items()


class TableOfContentsViewlet(ViewletBase):
    index = ViewPageTemplateFile("toc.pt")

    def update(self):
        obj = aq_base(self.context)
        getTableContents = getattr(obj, "getTableContents", None)
        self.enabled = False
        if getTableContents is not None:
            try:
                self.enabled = getTableContents()
            except KeyError:
                # schema not updated yet
                self.enabled = False
        # handle dexterity-behavior
        toc = getattr(obj, "table_of_contents", None)
        if toc is not None:
            self.enabled = toc


class SiteActionsViewlet(ViewletBase):
    index = ViewPageTemplateFile("site_actions.pt")

    def update(self):
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        self.site_actions = context_state.actions("site_actions")


class SearchBoxViewlet(ViewletBase):
    index = ViewPageTemplateFile("searchbox.pt")

    def update(self):
        super().update()

        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )

        registry = getUtility(IRegistry)
        search_settings = registry.forInterface(ISearchSchema, prefix="plone")
        self.livesearch = search_settings.enable_livesearch
        self.show_images = search_settings.search_show_images

        folder = context_state.folder()
        self.folder_path = "/".join(folder.getPhysicalPath())


class LogoViewlet(ViewletBase):
    index = ViewPageTemplateFile("logo.pt")

    def update(self):
        super().update()

        # TODO: should this be changed to settings.site_title?
        self.navigation_root_title = self.portal_state.navigation_root_title()

        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        self.logo_title = settings.site_title
        self.img_src = getSiteLogo()


class GlobalSectionsViewlet(ViewletBase):
    index = ViewPageTemplateFile("sections.pt")

    _opener_markup_template = (
        '<input id="navitem-{uid}" type="checkbox" class="opener" />'
        '<label for="navitem-{uid}" role="button" aria-label="{title}"></label>'  # noqa: E 501
    )
    _item_markup_template = (
        '<li class="{id}{has_sub_class} nav-item">'
        '<a href="{url}" class="state-{review_state} nav-link"{aria_haspopup}>{title}</a>{opener}'  # noqa: E 501
        "{sub}"
        "</li>"
    )
    _subtree_markup_wrapper = '<ul class="has_subtree dropdown">{out}</ul>'

    def __init__(self, *args):
        super().__init__(*args)
        self.registry = getUtility(IRegistry)

    @property
    def settings(self):
        return self.registry.forInterface(INavigationSchema, prefix="plone")

    @property
    def language_settings(self):
        return self.registry.forInterface(ILanguageSchema, prefix="plone")

    @property
    def navtree_path(self):
        return getNavigationRoot(self.context)

    @property
    def current_language(self):
        language_settings = self.registry.forInterface(ILanguageSchema, prefix="plone")
        return (
            self.request.get("LANGUAGE", None)
            or (self.context and aq_inner(self.context).Language())
            or language_settings.default_language
        )

    @property
    def types_using_view(self):
        return self.registry.get("plone.types_use_view_action_in_listings", [])

    @property
    @memoize
    def navtree(self):
        ret = defaultdict(list)
        navtree_path = self.navtree_path
        portal_tabs = self.portal_tabs
        for tab in portal_tabs:
            entry = tab.copy()
            entry.update(
                {
                    "path": "/".join((navtree_path, tab["id"])),
                    "uid": tab["id"],
                }
            )
            if "review_state" not in entry:
                entry["review_state"] = None

            if "title" not in entry:
                entry["title"] = tab.get("name") or tab.get("description") or tab["id"]
            else:
                # translate Home tab
                entry["title"] = translate(
                    entry["title"], domain="plone", context=self.request
                )

            entry["title"] = escape(safe_text(entry["title"]))
            if "name" in entry and entry["name"]:
                entry["name"] = escape(safe_text(entry["name"]))
            self.customize_tab(entry, tab)
            ret[navtree_path].append(entry)

        settings = self.settings
        if not settings.generate_tabs:
            return ret

        query = {
            "path": {
                "query": self.navtree_path,
                "depth": settings.navigation_depth,
            },
            "portal_type": {"query": settings.displayed_types},
            "Language": self.current_language,
            "sort_on": settings.sort_tabs_on,
            "is_default_page": False,
        }

        if settings.sort_tabs_reversed:
            query["sort_order"] = "reverse"

        if not settings.nonfolderish_tabs:
            query["is_folderish"] = True

        if settings.filter_on_workflow:
            query["review_state"] = list(settings.workflow_states_to_show or ())

        if not settings.show_excluded_items:
            query["exclude_from_nav"] = False

        context_path = "/".join(self.context.getPhysicalPath())
        self.customize_query(query)
        portal_catalog = getToolByName(self.context, "portal_catalog")
        brains = portal_catalog.searchResults(**query)

        types_using_view = set(self.types_using_view)
        for brain in brains:
            brain_path = brain.getPath()
            brain_parent_path = brain_path.rpartition("/")[0]
            if portal_tabs and brain_parent_path == navtree_path:
                # This should be already provided by the portal_tabs_view
                continue
            if brain.exclude_from_nav and not context_path.startswith(brain_path):
                # skip excluded items if they're not in our context path
                continue
            url = brain.getURL()
            if brain.portal_type in types_using_view:
                url += "/view"
            entry = {
                "id": brain.getId,
                "path": brain_path,
                "uid": brain.UID,
                "url": url,
                "title": escape(safe_text(brain.Title)),
                "review_state": brain.review_state,
            }
            self.customize_entry(entry, brain)
            ret[brain_parent_path].append(entry)

        return ret

    def customize_query(self, query):
        """Helper to customize the catalog query."""
        pass

    def customize_tab(self, entry, tab):
        """Helper to add custom entry keys/values."""
        pass

    def customize_entry(self, entry, brain):
        """Helper to add custom entry keys/values."""
        pass

    def render_item(self, item, path):
        sub = self.build_tree(item["path"], first_run=False)
        if sub:
            item.update(
                {
                    "sub": sub,
                    "opener": self._opener_markup_template.format(**item),
                    "aria_haspopup": ' aria-haspopup="true"',
                    "has_sub_class": " has_subtree",
                }
            )
        else:
            item.update(
                {
                    "sub": sub,
                    "opener": "",
                    "aria_haspopup": "",
                    "has_sub_class": "",
                }
            )
        return self._item_markup_template.format(**item)

    def build_tree(self, path, first_run=True):
        """Non-template based recursive tree building.
        3-4 times faster than template based.
        """
        out = ""
        for item in self.navtree.get(path, []):
            out += self.render_item(item, path)

        if not first_run and out:
            out = self._subtree_markup_wrapper.format(out=out)
        return out

    def render_globalnav(self):
        return self.build_tree(self.navtree_path)

    @property
    @memoize
    def portal_tabs(self):
        portal_tabs_view = getMultiAdapter(
            (self.context, self.request), name="portal_tabs_view"
        )
        return portal_tabs_view.topLevelTabs()


class PersonalBarViewlet(ViewletBase):

    homelink_url = ""
    user_name = ""

    def update(self):
        super().update()
        context = aq_inner(self.context)

        context_state = getMultiAdapter(
            (context, self.request), name="plone_context_state"
        )

        user_actions = context_state.actions("user")
        self.user_actions = []
        for action in user_actions:
            info = {
                "title": action["title"],
                "href": action["url"],
                "id": "personaltools-{}".format(action["id"]),
                "target": action.get("link_target", None),
                "icon": action.get("icon", None),
            }
            modal = action.get("modal")
            if modal:
                info["class"] = "pat-plone-modal"
                if '"title":' in modal:
                    modal = json.loads(modal)
                    modal["title"] = translate(_(modal["title"]), context=self.request)
                    modal = json.dumps(modal)

                info["data-pat-plone-modal"] = modal
            self.user_actions.append(info)

        self.anonymous = self.portal_state.anonymous()

        if not self.anonymous:
            member = self.portal_state.member()
            userid = member.getId()

            self.homelink_url = f"{self.navigation_root_url}/useractions"

            membership = getToolByName(context, "portal_membership")
            member_info = membership.getMemberInfo(userid)
            # member_info is None if there's no Plone user object, as when
            # using OpenID.
            if member_info:
                fullname = member_info.get("fullname", "")
            else:
                fullname = None
            if fullname:
                self.user_name = fullname
            else:
                self.user_name = userid


class ContentViewsViewlet(ViewletBase):
    index = ViewPageTemplateFile("contentviews.pt")
    menu_template = ViewPageTemplateFile("menu.pt")

    default_tab = "nothing"
    primary = ["folderContents", "edit", "view"]

    def update(self):
        # The drop-down menus are pulled in via a simple content provider
        # from plone.app.contentmenu. This behaves differently depending on
        # whether the view is marked with IViewView. If our parent view
        # provides that marker, we should do it here as well.
        super().update()
        if IViewView.providedBy(self.__parent__):
            alsoProvides(self, IViewView)

        self.tabSet1, self.tabSet2 = self.getTabSets()

    @memoize
    def getTabSets(self):
        context = aq_inner(self.context)
        context_url = context.absolute_url()
        context_fti = context.getTypeInfo()

        context_state = getMultiAdapter(
            (context, self.request), name="plone_context_state"
        )
        actions = context_state.actions

        action_list = []
        if context_state.is_structural_folder():
            action_list = actions("folder")
        action_list.extend(actions("object"))
        action_list.extend(actions("object_actions"))

        tabSet1 = []
        tabSet2 = []
        found_selected = False
        fallback_action = None

        try:
            request_url = self.request["ACTUAL_URL"]
        except KeyError:
            # not a real request, could be a test. Let's not fail.
            request_url = context_url
        request_url_path = request_url[len(context_url) :]

        if request_url_path.startswith("/"):
            request_url_path = request_url_path[1:]

        for item in action_list:
            item.update({"selected": False})

            action_url = item["url"].strip()
            starts = action_url.startswith
            if starts("http") or starts("javascript"):
                item["url"] = action_url
            else:
                item["url"] = f"{context_url}/{action_url}"
            item["url"] = addTokenToUrl(item["url"], self.request)

            action_method = item["url"].split("/")[-1].split("?")[0]

            # Action method may be a method alias:
            # Attempt to resolve to a template.
            action_method = context_fti.queryMethodID(
                action_method, default=action_method
            )
            if action_method:
                request_action = unquote(request_url_path).split("?")[0]
                request_action = context_fti.queryMethodID(
                    request_action, default=request_action
                )
                if action_method == request_action and item["id"] != "view":
                    item["selected"] = True
                    found_selected = True

            current_id = item["id"]
            if current_id == self.default_tab:
                fallback_action = item

            modal = item.get("modal", None)
            item["cssClass"] = ""
            if modal:
                item["cssClass"] += " pat-plone-modal"
                if "ajax_load" not in item["url"]:
                    item["url"] += "?ajax_load=1"

            if item["id"] in self.primary:
                tabSet1.append(item)
            else:
                tabSet2.append(item)

        if not found_selected and fallback_action is not None:
            fallback_action["selected"] = True

        tabSet1.sort(key=lambda item: self.primary.index(item["id"]))
        return tabSet1, tabSet2

    def locked_icon(self):
        if not getSecurityManager().checkPermission(
            "Modify portal content", self.context
        ):
            return ""

        locked = False
        lock_info = queryMultiAdapter(
            (self.context, self.request), name="plone_lock_info"
        )
        if lock_info is not None:
            locked = lock_info.is_locked()
        else:
            context = aq_inner(self.context)
            lockable = getattr(context.aq_explicit, "wl_isLocked", None) is not None
            locked = lockable and context.wl_isLocked()

        if not locked:
            return ""

        portal = self.portal_state.portal()
        icon = portal.restrictedTraverse("lock_icon.png")
        return icon.tag(title="Locked")


class PathBarViewlet(ViewletBase):
    index = ViewPageTemplateFile("path_bar.pt")

    def update(self):
        super().update()

        self.is_rtl = self.portal_state.is_rtl()

        breadcrumbs_view = getMultiAdapter(
            (self.context, self.request), name="breadcrumbs_view"
        )
        self.breadcrumbs = breadcrumbs_view.breadcrumbs()


class TinyLogoViewlet(ViewletBase):
    index = ViewPageTemplateFile("tiny_logo.pt")
