from AccessControl import getSecurityManager
from plone.app.layout.globals.interfaces import IBodyClassAdapter
from plone.app.layout.globals.interfaces import ILayoutPolicy
from plone.app.layout.globals.interfaces import IViewView
from plone.base.interfaces.controlpanel import ILinkSchema
from plone.base.interfaces.controlpanel import ISiteSchema
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize.view import memoize
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletManagerRenderer
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.metaconfigure import ViewMixinForTemplates
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.browserpage.viewpagetemplatefile import (
    ViewPageTemplateFile as ZopeViewPageTemplateFile,
)
from zope.component import adapter
from zope.component import getAdapters
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.browser import BrowserView

import json


TEMPLATE_CLASSES = (
    ViewPageTemplateFile,
    ZopeViewPageTemplateFile,
    ViewMixinForTemplates,
)


@implementer(ILayoutPolicy)
class LayoutPolicy(BrowserView):
    """A view that gives access to various layout related functions."""

    @property
    @memoize
    def _context_state(self):
        return getMultiAdapter((self.context, self.request), name="plone_context_state")

    def mark_view(self, view):
        """Adds a marker interface to the view if it is "the" view for the
        context May only be called from a template.
        """
        if not view:
            return
        if self._context_state.is_view_template() and not IViewView.providedBy(view):
            alsoProvides(view, IViewView)

    def hide_columns(self, column_left, column_right):
        """Returns a CSS class matching the current column status."""
        if not column_right and not column_left:
            return "visualColumnHideOneTwo"
        if column_right and not column_left:
            return "visualColumnHideOne"
        if not column_right and column_left:
            return "visualColumnHideTwo"
        return "visualColumnHideNone"

    def have_portlets(self, manager_name, view=None):
        """Determine whether a column should be shown. The left column is
        called plone.leftcolumn; the right column is called plone.rightcolumn.
        """
        force_disable = self.request.get("disable_" + manager_name, None)
        if force_disable is not None:
            return not bool(force_disable)

        context = self.context
        if view is None:
            view = self

        manager = queryUtility(IPortletManager, name=manager_name)
        if manager is None:
            return False

        renderer = queryMultiAdapter(
            (context, self.request, view, manager), IPortletManagerRenderer
        )
        if renderer is None:
            renderer = getMultiAdapter(
                (context, self.request, self, manager), IPortletManagerRenderer
            )

        return renderer.visible

    def _image_visibility(self, name):
        """check if image {name} is visible with current settings and user"""
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        visibility = getattr(settings, f"{name}_visibility")
        if visibility == "enabled":
            return True
        if visibility != "authenticated":
            return False
        user = getSecurityManager().getUser()
        return user is not None and user.getUserName() != "Anonymous User"

    @memoize
    def icons_visible(self):
        """Returns True if icons should be shown or False otherwise."""
        return self._image_visibility("icon")

    @memoize
    def thumb_visible(self):
        """Returns True if thumbs should be shown or False otherwise."""
        return self._image_visibility("thumb")

    def _toolbar_classes(self):
        """current toolbar controlling classes"""
        if not self._context_state.is_toolbar_visible():
            return set()

        toolbar_classes = set()
        registry = getUtility(IRegistry)
        site_settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        try:
            left = site_settings.toolbar_position == "side"
        except KeyError:
            left = True
        if left:
            toolbar_classes.add("plone-toolbar-left")
        else:
            toolbar_classes.add("plone-toolbar-top")
        try:
            toolbar_state = {}
            toolbar_state_cookie = self.request.cookies.get("plone-toolbar")
            if toolbar_state_cookie:
                toolbar_state = json.loads(toolbar_state_cookie)
            if toolbar_state.get("expanded", True):
                toolbar_classes.add("plone-toolbar-expanded")
                if left:
                    toolbar_classes.add("plone-toolbar-left-expanded")
                else:
                    toolbar_classes.add("plone-toolbar-top-expanded")
            else:
                if left:
                    toolbar_classes.add("plone-toolbar-left-default")
                else:
                    toolbar_classes.add("plone-toolbar-top-default")
        except Exception:
            pass
        return toolbar_classes

    def _template_name(self, template, view):
        """Name of template.

        Sometimes it is best to take this from the template, sometimes the view.
        Note that neither template nor view are always available.
        For example, mosaic passes a view but not a template.
        """
        view_name = view.__name__ if view else ""
        if isinstance(template, TEMPLATE_CLASSES):
            # Browser view.  Take the view name.
            # But it this is 'index.html', it may be the error message view.
            # It is better to take the template name then.
            if view_name != "index.html":
                return view_name
        # template can be SimpleViewClass, which has no getId.
        # Probably caught above with isinstance(template, TEMPLATE_CLASSES),
        # but let's be careful.
        if template and hasattr(template, "getId"):
            template_name = template.getId()
            if template_name:
                return template_name
        return view_name

    def bodyClass(self, template, view):
        """
        Returns the CSS class to be used on the body tag.

        Included body classes:
        - template-{}: template name
        - portaltype-{}: portal type
        - site-{}: navigation root
        - section-{}: first section name
        - subsection-{}: subsection names until configured depth
        - icons-on: show icons
        - icons-off: hide icons
        - thumbs-on: show thumbnails
        - thumbs-off: hide thumbnails
        - frontend: user without privileges, no admin interfaces shown
        - viewpermission-{}: minimum permission needed to view context
        - userrole-anonymous: anonymous user
        - userrole-{}: user roles for current user
        - plone-toolbar-left: toolbar is shown on left side
        - plone-toolbar-top: toolbar is shown on top
        - plone-toolbar-expanded: toolbar is in expanded state
        - plone-toolbar-left-expanded: left toolbar is expanded
        - plone-toolbar-top-expanded: top toolbar is expanded
        - plone-toolbar-left-default: left toolbar is not expanded
        - plone-toolbar-top-default: top toolbar is not expanded
        - pat-markspeciallinks: mark special links is set
        """
        portal_state = getMultiAdapter(
            (self.context, self.request), name="plone_portal_state"
        )
        normalizer = queryUtility(IIDNormalizer)
        registry = getUtility(IRegistry)

        body_classes = self._toolbar_classes()

        # template class (required)
        template_name = self._template_name(template, view)
        if template_name:
            template_name = normalizer.normalize(template_name)
            body_classes.add("template-%s" % template_name)

        # portal type class (optional)
        portal_type = normalizer.normalize(self.context.portal_type)
        if portal_type:
            body_classes.add("portaltype-%s" % portal_type)

        # section class (optional)
        navroot = portal_state.navigation_root()
        body_classes.add("site-%s" % navroot.getId())

        contentPath = self.context.getPhysicalPath()[len(navroot.getPhysicalPath()) :]
        if contentPath:
            body_classes.add("section-%s" % contentPath[0])
            # skip first section since we already have that...
            if len(contentPath) > 1:
                depth = registry.get("plone.app.layout.globals.bodyClass.depth", 4)
                if depth > 1:
                    classes = ["subsection-%s" % contentPath[1]]
                    for section in contentPath[2:depth]:
                        classes.append("-".join([classes[-1], section]))
                    body_classes.update(classes)

        # class for hiding icons (optional)
        if self.icons_visible():
            body_classes.add("icons-on")
        else:
            body_classes.add("icons-off")

        # class for hiding thumbs (optional)
        if self.thumb_visible():
            body_classes.add("thumbs-on")
        else:
            body_classes.add("thumbs-off")

        # classes for column visibility: col-content, col-one, col-two:
        body_classes.add("col-content")
        if self.have_portlets("plone.leftcolumn", view):
            body_classes.add("col-one")
        if self.have_portlets("plone.rightcolumn", view):
            body_classes.add("col-two")

        # permissions required. Useful to theme frontend and backend
        # differently
        permissions = []
        if not getattr(view, "__ac_permissions__", tuple()):
            permissions = ["none"]
        for permission, roles in getattr(view, "__ac_permissions__", tuple()):
            permissions.append(normalizer.normalize(permission))
        if "none" in permissions or "view" in permissions:
            body_classes.add("frontend")
        for permission in permissions:
            body_classes.add("viewpermission-" + permission)

        # class for user roles
        membership = getToolByName(self.context, "portal_membership")
        if membership.isAnonymousUser():
            body_classes.add("userrole-anonymous")
        else:
            user = membership.getAuthenticatedMember()
            for role in user.getRolesInContext(self.context):
                body_classes.add("userrole-" + role.lower().replace(" ", "-"))

        # class for markspeciallinks pattern
        link_settings = registry.forInterface(ILinkSchema, prefix="plone", check=False)
        msl = link_settings.mark_special_links
        elonw = link_settings.external_links_open_new_window
        if msl or elonw:
            body_classes.add("pat-markspeciallinks")

        # Add externally defined extra body classes
        body_class_adapters = getAdapters(
            (self.context, self.request), IBodyClassAdapter
        )
        for name, body_class_adapter in body_class_adapters:
            try:
                extra_classes = body_class_adapter.get_classes(template, view) or []
            except TypeError:  # This adapter is implemented without arguments
                extra_classes = body_class_adapter.get_classes() or []
            if isinstance(extra_classes, str):
                extra_classes = extra_classes.split(" ")
            body_classes.update(extra_classes)

        return " ".join(sorted(body_classes))


@adapter(Interface)
@implementer(IBodyClassAdapter)
class DefaultBodyClasses:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_classes(self, template, view):
        """Default body classes adapter."""
        return []
