from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from DateTime import DateTime
from plone.base import PloneMessageFactory as _
from plone.base.defaultpage import check_default_page_via_view
from plone.base.utils import transaction_note
from plone.protect import CheckAuthenticator
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from ZODB.POSException import ConflictError
from zope.component import getMultiAdapter
from zope.component import getUtility


class ContentStatusModifyView(BrowserView):
    """Handles the workflow transitions of objects.

    Former Controller Python Script "content_status_modify".

    [validators]
    validators = validate_content_status_modify

    [actions]
    action.failure=traverse_to:string:content_status_history
    action.success=redirect_to_action:string:view

    """

    def __call__(
        self,
        workflow_action=None,
        comment="",
        effective_date=None,
        expiration_date=None,
        **kwargs,
    ):
        """Do a workflow action.

        The status dropdown in the toolbar has links to for example:
        content_status_modify?workflow_action=reject&_authenticator=secret
        That is the main entry into this browser view.

        When you right-click the status menu and open in a new tab,
        you end up on the content_status_history page.
        This page contains a form which posts to this view.

        In the form you can select a workflow action.
        When you select "no change" the workflow_action parameter actually contains
        the current status.  This status is naturally not in the list of allowed transitions.
        So we should be lenient here, and not complain much.

        Also, when the view is called on a default page,
        the code below tries to do the same transition on the parent folder,
        by calling this view on the parent.  This may easily fail.
        This is yet another reason to be lenient.
        Otherwise you may see both a successful portal status message
        and one with an error.

        In the form you can also add a comment and set an effective and/or expiration date.
        """
        context = aq_inner(self.context)
        portal_workflow = getToolByName(context, "portal_workflow")
        self.plone_utils = getToolByName(context, "plone_utils")
        # First check if the main argument is given.
        if not workflow_action:
            IStatusMessage(self.request).add(
                _("You must select a publishing action."), type="error"
            )
            url = f"{context.absolute_url()}/content_status_history"
            return self.request.response.redirect(url)
        # If a workflow action was specified, there must be a plone.protect authenticator.
        CheckAuthenticator(self.request)

        # Get effective and expiration dates from the form, if not set in the arguments.
        form = self.request.form
        if not effective_date:
            effective_date = form.get("form.widgets.effective_date") or effective_date
        if not expiration_date:
            expiration_date = (
                form.get("form.widgets.expiration_date") or expiration_date
            )

        # Make sure an effective date is always set when there is a valid workflow action.
        transitions = portal_workflow.getTransitionsFor(context)
        transition_ids = [t["id"] for t in transitions]
        if (
            workflow_action in transition_ids
            and not effective_date
            and context.EffectiveDate() == "None"
        ):
            effective_date = DateTime()

        # You can transition content but not have the permission to ModifyPortalContent.
        contentEditSuccess = 0
        try:
            self.editContent(context, effective_date, expiration_date)
            contentEditSuccess = 1
        except Unauthorized:
            pass

        # Create the note while we still have access to the original context
        note = "Changed status of {} at {}".format(
            context.title_or_id(),
            context.absolute_url(),
        )

        if workflow_action in transition_ids:
            # The action could result in a move or delete.
            # In that case we get a new context as answer.
            context = portal_workflow.doActionFor(
                context, workflow_action, comment=comment
            )
            if context is None:
                # the normal case
                context = aq_inner(self.context)

        # The object post-transition could now have ModifyPortalContent permission.
        if not contentEditSuccess:
            try:
                self.editContent(context, effective_date, expiration_date)
            except Unauthorized:
                pass

        transaction_note(note)

        # If this item is the default page in its parent, attempt to publish that
        # too. It may not be possible, of course
        if check_default_page_via_view(context, self.request):
            parent = aq_parent(context)
            try:
                parent_modify_view = getMultiAdapter(
                    (parent, self.request), name="content_status_modify"
                )
                parent_modify_view(
                    workflow_action,
                    comment,
                    effective_date=effective_date,
                    expiration_date=expiration_date,
                )
            except ConflictError:
                raise
            except Exception:
                pass

        IStatusMessage(self.request).add(_("Item state changed."))
        registry = getUtility(IRegistry)
        url = context.absolute_url()
        if context.portal_type in registry.get(
            "plone.types_use_view_action_in_listings", ()
        ):
            url += "/view"
        return self.request.response.redirect(url)

    def editContent(self, obj, effective, expiry):
        kwargs = {}
        # may contain the year
        if effective and (isinstance(effective, DateTime) or len(effective) > 5):
            kwargs["effective_date"] = effective
        # may contain the year
        if expiry and (isinstance(expiry, DateTime) or len(expiry) > 5):
            kwargs["expiration_date"] = expiry
        self.plone_utils.contentEdit(obj, **kwargs)
