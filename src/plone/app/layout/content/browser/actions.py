from AccessControl import getSecurityManager
from Acquisition import aq_inner
from Acquisition import aq_parent
from OFS.CopySupport import CopyError
from plone.base import PloneMessageFactory as _
from plone.base.utils import get_user_friendly_types
from plone.base.utils import safe_text
from plone.locking.interfaces import ILockable
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.widget import ComputedWidgetAttribute
from zExceptions import Unauthorized
from ZODB.POSException import ConflictError
from zope import schema
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.interface import Interface
from zope.lifecycleevent import ObjectModifiedEvent

import transaction


class LockingBase(BrowserView):
    @property
    def is_locked(self):
        locking_view = queryMultiAdapter(
            (self.context, self.request), name="plone_lock_info"
        )

        return locking_view and locking_view.is_locked_for_current_user()


class DeleteConfirmationForm(form.Form, LockingBase):
    fields = field.Fields()
    template = ViewPageTemplateFile("templates/delete_confirmation.pt")
    enableCSRFProtection = True

    def view_url(self):
        """Facade to the homonymous plone_context_state method"""
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        return context_state.view_url()

    def more_info(self):
        adapter = queryMultiAdapter(
            (self.context, self.request), name="delete_confirmation_info"
        )
        if adapter:
            return adapter()
        return ""

    @property
    def items_to_delete(self):
        catalog = getToolByName(self.context, "portal_catalog")
        results = catalog(
            {
                "path": "/".join(self.context.getPhysicalPath()),
                "portal_type": get_user_friendly_types(),
            }
        )
        return len(results)

    @button.buttonAndHandler(_("Delete"), name="Delete")
    def handle_delete(self, action):
        title = safe_text(self.context.Title())
        parent = aq_parent(aq_inner(self.context))

        # has the context object been acquired from a place it should not have
        # been?
        if self.context.aq_chain == self.context.aq_inner.aq_chain:
            try:
                lock_info = self.context.restrictedTraverse("@@plone_lock_info")
            except AttributeError:
                lock_info = None
            if lock_info is not None:
                if lock_info.is_locked() and not lock_info.is_locked_for_current_user():
                    # unlock object as it is locked by current user
                    ILockable(self.context).unlock()
            parent.manage_delObjects(self.context.getId())
            IStatusMessage(self.request).add(
                _("${title} has been deleted.", mapping={"title": title})
            )
        else:
            IStatusMessage(self.request).add(
                _('"${title}" has already been deleted', mapping={"title": title})
            )

        self.request.response.redirect(parent.absolute_url())

    @button.buttonAndHandler(_("label_cancel", default="Cancel"), name="Cancel")
    def handle_cancel(self, action):
        target = self.view_url()
        return self.request.response.redirect(target)

    def updateActions(self):
        super().updateActions()
        if self.actions and "Delete" in self.actions:
            self.actions["Delete"].addClass("btn-danger")
        if self.actions and "Cancel" in self.actions:
            self.actions["Cancel"].addClass("btn-secondary")


def valid_id(self):
    # TODO: Do we need an validator here or use the same that's used in
    #       plone.app.dexterity.behaviors.id.IShortName
    return True


class IRenameForm(Interface):
    new_id = schema.ASCIILine(
        title=_("label_new_short_name", default="New Short Name"),
        description=_(
            "help_short_name_url",
            default="Short name is the part that shows up in the URL " + "of the item.",
        ),
        constraint=valid_id,
    )

    new_title = schema.TextLine(
        title=_("label_new_title", default="New Title"),
    )


default_new_id = ComputedWidgetAttribute(
    lambda form: form.context.getId(), field=IRenameForm["new_id"]
)

default_new_title = ComputedWidgetAttribute(
    lambda form: form.context.Title(), field=IRenameForm["new_title"]
)


class RenameForm(form.Form):
    fields = field.Fields(IRenameForm)
    template = ViewPageTemplateFile("templates/object_rename.pt")
    enableCSRFProtection = True
    ignoreContext = True

    label = _("heading_rename_item", default="Rename item")
    description = _(
        "description_rename_item",
        default="Each item has a Short Name and a Title, which you can "
        + "change by entering the new details below.",
    )

    def view_url(self):
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        return context_state.view_url()

    @button.buttonAndHandler(_("Rename"), name="Rename")
    def handle_rename(self, action):
        data, errors = self.extractData()
        if errors:
            return

        parent = aq_parent(aq_inner(self.context))
        sm = getSecurityManager()
        if not sm.checkPermission("Copy or Move", parent):
            raise Unauthorized(
                _(
                    "Permission denied to rename ${title}.",
                    mapping={"title": self.context.title},
                )
            )

        # Requires cmf.ModifyPortalContent permission
        self.context.title = data["new_title"]

        oldid = self.context.getId()
        newid = data["new_id"]
        if oldid != newid:
            newid = INameChooser(parent).chooseName(newid, self.context)

            # Requires zope2.CopyOrMove permission

            # manage_renameObjects fires 3 events:
            # 1. ObjectWillBeMovedEvent before anything happens
            # 2. ObjectMovedEvent directly after rename
            # 3. zope.container.contained.notifyContainerModified directly after 2
            # for 2+3 there are subscribers in Products.CMFDynamicViewFTI
            # responsible to change (2) or unset (3) the default_page.

            parent.manage_renameObjects(
                [
                    oldid,
                ],
                [
                    str(newid),
                ],
            )
        else:
            # Object is not reindex if manage_renameObjects is not called
            self.context.reindexObject()

        transaction.savepoint(optimistic=True)
        notify(ObjectModifiedEvent(self.context))

        IStatusMessage(self.request).add(
            _(
                "Renamed '${oldid}' to '${newid}'.",
                mapping={"oldid": oldid, "newid": newid},
            )
        )

        self.request.response.redirect(self.view_url())

    @button.buttonAndHandler(_("label_cancel", default="Cancel"), name="Cancel")
    def handle_cancel(self, action):
        self.request.response.redirect(self.view_url())

    def updateActions(self):
        super().updateActions()
        if self.actions and "Rename" in self.actions:
            self.actions["Rename"].addClass("btn-primary")
        if self.actions and "Cancel" in self.actions:
            self.actions["Cancel"].addClass("btn-secondary")


class ObjectCutView(BrowserView):
    @property
    def title(self):
        return self.context.Title()

    @property
    def parent(self):
        return aq_parent(aq_inner(self.context))

    @property
    def canonical_object_url(self):
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        return context_state.canonical_object_url()

    @property
    def view_url(self):
        context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        return context_state.view_url()

    def do_redirect(self, url, message=None, message_type="info", raise_exception=None):
        if message is not None:
            IStatusMessage(self.request).add(message, type=message_type)

        if raise_exception is None:
            return self.request.response.redirect(url)
        raise raise_exception

    def do_action(self):
        try:
            lock_info = self.context.restrictedTraverse("@@plone_lock_info")
        except AttributeError:
            lock_info = None
        if lock_info is not None:
            if lock_info.is_locked_for_current_user():
                return self.do_redirect(
                    self.view_url,
                    _(
                        "${title} is locked and cannot be cut.",
                        mapping={
                            "title": self.title,
                        },
                    ),
                )
            elif lock_info.is_locked():
                # unlock object as it is locked by current user
                ILockable(self.context).unlock()

        try:
            cp = self.parent.manage_cutObjects(self.context.getId())
        except CopyError:
            return self.do_redirect(
                self.view_url,
                _("${title} is not moveable.", mapping={"title": self.title}),
            )
        self.request.response.setCookie(
            "__cp", cp, path=self.request["BASEPATH1"] or "/"
        )
        self.request["__cp"] = cp

        return self.do_redirect(
            self.view_url, _("${title} cut.", mapping={"title": self.title}), "info"
        )

    def __call__(self):
        authenticator = getMultiAdapter(
            (self.context, self.request), name="authenticator"
        )

        if not authenticator.verify():
            raise Unauthorized

        return self.do_action()


class ObjectCopyView(ObjectCutView):
    def do_action(self):
        try:
            cp = self.parent.manage_copyObjects(self.context.getId())
        except CopyError:
            return self.do_redirect(
                self.view_url,
                _("${title} is not copyable.", mapping={"title": self.title}),
            )
        self.request.response.setCookie(
            "__cp", cp, path=self.request["BASEPATH1"] or "/"
        )
        self.request["__cp"] = cp

        return self.do_redirect(
            self.view_url, _("${title} copied.", mapping={"title": self.title})
        )


class ObjectDeleteView(ObjectCutView):
    def do_action(self):
        form = DeleteConfirmationForm(self.context, self.request)
        form.update()

        button = form.buttons["Delete"]
        # delete by clicking the form button in delete_confirmation
        form.handlers.getHandler(button)(form, button)


class ObjectPasteView(ObjectCutView):
    def do_action(self):
        if not self.context.cb_dataValid():
            return self.do_redirect(
                self.canonical_object_url,
                _("Copy or cut one or more items to paste."),
                "error",
            )
        try:
            self.context.manage_pasteObjects(self.request["__cp"])
        except ConflictError:
            raise
        except Unauthorized as e:
            self.do_redirect(
                self.canonical_object_url, _("You are not authorized to paste here."), e
            )
        except CopyError as e:
            error_string = str(e)
            if "Item Not Found" in error_string:
                return self.do_redirect(
                    self.canonical_object_url,
                    _(
                        "The item you are trying to paste could not be found. "
                        "It may have been moved or deleted after you copied or "
                        "cut it."
                    ),
                    "error",
                )
        except Exception as e:
            if "__cp" in self.request:
                self.do_redirect(self.canonical_object_url, e, "error", e)

        return self.do_redirect(self.canonical_object_url, _("Item(s) pasted."))
