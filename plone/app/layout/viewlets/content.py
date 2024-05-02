from AccessControl import getSecurityManager
from Acquisition import aq_inner
from DateTime import DateTime
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from plone.app.layout.viewlets import ViewletBase
from plone.app.relationfield.behavior import IRelatedItems
from plone.base import PloneMessageFactory as _
from plone.base.interfaces import ISecuritySchema
from plone.base.interfaces import ISiteSchema
from plone.base.utils import base_hasattr
from plone.base.utils import logger
from plone.memoize.instance import memoize
from plone.memoize.view import memoize_contextless
from plone.protect.authenticator import createToken
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFEditions.Permissions import AccessPreviousVersions
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from urllib.parse import urlencode
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.deprecation import deprecation


class DocumentActionsViewlet(ViewletBase):
    index = ViewPageTemplateFile("document_actions.pt")

    def update(self):
        super().update()

        self.context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        self.actions = self.context_state.actions("document_actions")


class DocumentBylineViewlet(ViewletBase):
    index = ViewPageTemplateFile("document_byline.pt")

    def update(self):
        super().update()
        self.anonymous = self.portal_state.anonymous()

    @property
    @deprecation.deprecate(
        "The context_state property is unused and will be removed in Plone 7"
    )
    def context_state(self):
        return getMultiAdapter((self.context, self.request), name="plone_context_state")

    @property
    @deprecation.deprecate(
        "The has_pam property is unused and will be removed in Plone 7"
    )
    def has_pam(self):
        return True

    @property
    @memoize_contextless
    def portal_membership(self):
        return getToolByName(self.context, "portal_membership")

    def show(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISiteSchema,
            prefix="plone",
            check=False,
        )
        return not self.anonymous or settings.display_publication_date_in_byline

    def show_about(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISecuritySchema,
            prefix="plone",
        )
        return not self.anonymous or settings.allow_anon_views_about

    @deprecation.deprecate(
        "The creator method is unused and will be removed in Plone 7"
    )
    def creator(self):
        return self.context.Creator()

    @deprecation.deprecate("The author method is unused and will be removed in Plone 7")
    def author(self):
        membership = getToolByName(self.context, "portal_membership")
        return membership.getMemberInfo(self.creator())

    @deprecation.deprecate(
        "The authorname method is unused and will be removed in Plone 7"
    )
    def authorname(self):
        author = self.author()
        return author and author["fullname"] or self.creator()

    @memoize
    def get_member_info(self, user_id):
        return self.portal_membership.getMemberInfo(user_id)

    def get_url_path(self, user_id):
        if self.get_member_info(user_id) is None:
            return ""
        if "/" in user_id:
            qs = urlencode({"author": user_id})
            return f"author/?{qs}"
        return f"author/{user_id}"

    def get_fullname(self, user_id):
        info = self.get_member_info(user_id)
        if info is None:
            return user_id
        return info.get("fullname") or user_id

    def show_modification_date(self):
        return not self.context.effective_date or (
            self.context.effective_date.Date() < self.context.modification_date.Date()
        )

    def isExpired(self):
        if base_hasattr(self.context, "expires"):
            return self.context.expires().isPast()
        return False

    @deprecation.deprecate(
        "The toLocalizedTime method is unused and will be removed in Plone 7"
    )
    def toLocalizedTime(self, time, long_format=None, time_only=None):
        """Convert time to localized time"""
        util = getToolByName(self.context, "translation_service")
        return util.ulocalized_time(
            time, long_format, time_only, self.context, domain="plonelocales"
        )

    def pub_date(self):
        """Return object effective date.

        Return None if publication date is switched off in global site settings
        or if Effective Date is not set on object.
        """
        # check if we are allowed to display publication date
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)

        if not settings.display_publication_date_in_byline:
            return None

        # check if we have Effective Date set
        date = self.context.EffectiveDate()
        if not date or date == "None":
            return None

        return DateTime(date)

    @deprecation.deprecate(
        "The get_translations method is unused and will be removed in Plone 7"
    )
    def get_translations(self):
        from plone.app.multilingual.browser.vocabularies import translated_languages
        from plone.app.multilingual.interfaces import ITranslatable
        from plone.app.multilingual.interfaces import ITranslationManager

        cts = []
        if ITranslatable.providedBy(self.context):
            t_langs = translated_languages(self.context)
            context_translations = ITranslationManager(self.context).get_translations()
            for lang in t_langs:
                cts.append(
                    dict(
                        lang_native=lang.title,
                        url=context_translations[lang.value].absolute_url(),
                    )
                )
        return cts


class HistoryByLineView(BrowserView):
    """DocumentByLine information for content history view"""

    index = ViewPageTemplateFile("history_view.pt")

    def update(self):
        context = self.context
        self.portal_state = getMultiAdapter(
            (context, self.request), name="plone_portal_state"
        )
        self.context_state = getMultiAdapter(
            (self.context, self.request), name="plone_context_state"
        )
        self.anonymous = self.portal_state.anonymous()

    def __call__(self):
        self.update()

        return self.index()

    @property
    @deprecation.deprecate(
        "The has_pam property is unused and will be removed in Plone 7"
    )
    def has_pam(self):
        return True

    def show(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISecuritySchema,
            prefix="plone",
        )
        return not self.anonymous or settings.allow_anon_views_about

    def show_history(self):
        has_access_preview_versions_permission = _checkPermission(
            "CMFEditions: Access previous versions", self.context
        )
        if not has_access_preview_versions_permission:
            return False
        if IViewView.providedBy(self.__parent__):
            return True
        if IFolderContentsView.providedBy(self.__parent__):
            return True
        return False

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

    def creator(self):
        return self.context.Creator()

    def author(self):
        membership = getToolByName(self.context, "portal_membership")
        return membership.getMemberInfo(self.creator())

    def authorname(self):
        author = self.author()
        return author and author["fullname"] or self.creator()

    def isExpired(self):
        if base_hasattr(self.context, "expires"):
            return self.context.expires().isPast()
        return False

    def toLocalizedTime(self, time, long_format=None, time_only=None):
        """Convert time to localized time"""
        util = getToolByName(self.context, "translation_service")
        return util.ulocalized_time(
            time, long_format, time_only, self.context, domain="plonelocales"
        )

    def pub_date(self):
        """Return object effective date.

        Return None if publication date is switched off in global site settings
        or if Effective Date is not set on object.
        """
        # check if we are allowed to display publication date
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)

        if not settings.display_publication_date_in_byline:
            return None

        # check if we have Effective Date set
        date = self.context.EffectiveDate()
        if not date or date == "None":
            return None

        return DateTime(date)

    @deprecation.deprecate(
        "The get_translations method is unused and will be removed in Plone 7"
    )
    def get_translations(self):
        from plone.app.multilingual.browser.vocabularies import translated_languages
        from plone.app.multilingual.interfaces import ITranslatable
        from plone.app.multilingual.interfaces import ITranslationManager

        cts = []
        if ITranslatable.providedBy(self.context):
            t_langs = translated_languages(self.context)
            context_translations = ITranslationManager(self.context).get_translations()
            for lang in t_langs:
                cts.append(
                    dict(
                        lang_native=lang.title,
                        url=context_translations[lang.value].absolute_url(),
                    )
                )

        return cts


class ContentRelatedItems(ViewletBase):
    index = ViewPageTemplateFile("document_relateditems.pt")

    def related_items(self):
        if not IRelatedItems.providedBy(self.context):
            return ()
        related = aq_inner(self.context).relatedItems
        if not related:
            return ()
        return self.related2brains(related)

    def related2brains(self, related):
        """Return a list of brains based on a list of relations. Will filter
        relations if the user has no permission to access the content.

        :param related: related items
        :type related: list of relations
        :return: list of catalog brains
        """
        catalog = getToolByName(self.context, "portal_catalog")
        brains = []
        for r in related:
            path = r.to_path
            if path is None:
                # Item was deleted.  The related item should have been cleaned
                # up, but apparently this does not happen.
                continue
            # the query will return an empty list if the user
            # has no permission to see the target object
            brains.extend(catalog(path=dict(query=path, depth=0)))
        return brains


class WorkflowHistoryViewlet(ViewletBase):
    index = ViewPageTemplateFile("review_history.pt")

    @memoize
    def getUserInfo(self, userid):
        actor = dict(fullname=userid)
        mt = getToolByName(self.context, "portal_membership")
        info = mt.getMemberInfo(userid)
        if info is None:
            return dict(actor_home="", actor=actor)

        fullname = info.get("fullname", None)
        if fullname:
            actor["fullname"] = fullname

        return dict(actor=actor, actor_home=f"{self.site_url}/author/{userid}")

    def workflowHistory(self, complete=True):
        """Return workflow history of this context.

        Taken from plone_scripts/getWorkflowHistory.py
        """
        context = aq_inner(self.context)
        # check if the current user has the proper permissions
        if not (
            _checkPermission("Request review", context)
            or _checkPermission("Review portal content", context)
        ):
            return []

        workflow = getToolByName(context, "portal_workflow")
        review_history = []

        try:
            # Get total history.
            # Note: expected variables like 'action' may not exist:
            # the workflow may have started out without variables.
            review_history = workflow.getInfoFor(context, "review_history")

            if not complete:
                # filter out automatic transitions.
                review_history = [r for r in review_history if r.get("action")]
            else:
                review_history = list(review_history)

            portal_type = context.portal_type
            anon = _("label_anonymous_user", default="Anonymous User")
            for r in review_history:
                r["type"] = "workflow"

                # Get transition title.
                transition_title = ""
                action = r.get("action")
                if action:
                    transition_title = workflow.getTitleForTransitionOnType(
                        action, portal_type
                    )
                if not transition_title:
                    transition_title = _("Create")
                r["transition_title"] = transition_title

                # Get state title.
                r["state_title"] = workflow.getTitleForStateOnType(
                    r.get("review_state", ""), portal_type
                )

                # Get actor.
                actorid = r.get("actor")
                r["actorid"] = actorid
                if actorid is None:
                    # action performed by an anonymous user, or unknown
                    r["actor"] = {"username": anon, "fullname": anon}
                    r["actor_home"] = ""
                else:
                    r.update(self.getUserInfo(actorid))
            review_history.reverse()

        except WorkflowException:
            logger.debug(
                "plone.app.layout.viewlets.content: %s has no associated workflow",
                context.absolute_url(),
            )

        return review_history


class ContentHistoryViewlet(WorkflowHistoryViewlet):
    index = ViewPageTemplateFile("content_history.pt")

    def revisionHistory(self):
        context = aq_inner(self.context)
        if not _checkPermission(AccessPreviousVersions, context):
            return []

        rt = getToolByName(context, "portal_repository", None)
        if rt is None or not rt.isVersionable(context):
            return []

        context_url = context.absolute_url()
        history = rt.getHistoryMetadata(context)
        portal_diff = getToolByName(context, "portal_diff", None)
        can_diff = (
            portal_diff is not None
            and len(portal_diff.getDiffForPortalType(context.portal_type)) > 0
        )
        can_revert = _checkPermission(
            "CMFEditions: Revert to previous versions", context
        )

        def morphVersionDataToHistoryFormat(vdata, version_id):
            meta = vdata["metadata"]["sys_metadata"]
            userid = meta["principal"]
            token = createToken()
            preview_url = (
                "%s/versions_history_form?version_id=%s&_authenticator=%s#version_preview"
                % (context_url, version_id, token)  # noqa
            )
            info = dict(
                type="versioning",
                action=_("Edited"),
                transition_title=_("Edited"),
                actorid=userid,
                time=meta["timestamp"],
                comments=meta["comment"],
                version_id=version_id,
                preview_url=preview_url,
            )
            if can_diff:
                if version_id > 0:
                    info["diff_previous_url"] = (
                        "{}/@@history?one={}&two={}&_authenticator={}".format(
                            context_url,
                            version_id,
                            version_id - 1,
                            token,
                        )
                    )
                if not rt.isUpToDate(context, version_id):
                    info["diff_current_url"] = (
                        "{}/@@history?one=current&two={}&_authenticator={}".format(
                            context_url,
                            version_id,
                            token,
                        )
                    )
            if can_revert:
                info["revert_url"] = "%s/revertversion" % context_url
            else:
                info["revert_url"] = None
            info.update(self.getUserInfo(userid))
            return info

        # History may be an empty list
        if not history:
            return history

        version_history = []
        retrieve = history.retrieve
        getId = history.getVersionId
        # Count backwards from most recent to least recent
        for i in range(history.getLength(countPurged=False) - 1, -1, -1):
            version_history.append(
                morphVersionDataToHistoryFormat(
                    retrieve(i, countPurged=False), getId(i, countPurged=False)
                )
            )

        return version_history

    def fullHistory(self):
        history = self.workflowHistory() + self.revisionHistory()
        if len(history) == 0:
            return None
        history.sort(key=lambda x: x.get("time", 0.0), reverse=True)
        return history

    def toLocalizedTime(self, time, long_format=None, time_only=None):
        """Convert time to localized time"""
        util = getToolByName(self.context, "translation_service")
        return util.ulocalized_time(
            time, long_format, time_only, self.context, domain="plonelocales"
        )


class ContentHistoryView(ContentHistoryViewlet):
    def __init__(self, context, request):
        super().__init__(context, request, None, None)
        self.update()

    def __call__(self):
        return self.index()
