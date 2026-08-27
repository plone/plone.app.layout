from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.app.layout.content.browser.tableview import Table
from plone.app.layout.content.browser.tableview import TableBrowserView
from plone.base.defaultpage import is_default_page
from plone.base.utils import human_readable_size
from plone.base.utils import is_expired
from plone.base.utils import safe_text
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from urllib.parse import quote_plus
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.publisher.browser import BrowserView


class FullReviewListView(BrowserView):
    def revlist(self):
        portal_membership = getToolByName(self.context, "portal_membership")
        portal_workflow = getToolByName(self.context, "portal_workflow")
        if portal_membership.isAnonymousUser():
            return []

        return portal_workflow.getWorklistsResults()

    def url(self):
        return self.context.absolute_url() + "/full_review_list"

    def review_table(self):
        table = ReviewListTable(self.context, self.request)
        return table.render()


class ReviewListTable:
    """
    The review list table renders the table and its actions.
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

        url = self.context.absolute_url()
        view_url = url + "/full_review_list"
        self.table = Table(request, url, view_url, self.items, buttons=self.buttons)

    def render(self):
        return self.table.render()

    @property
    def items(self):
        portal_url = getToolByName(self.context, "portal_url")
        plone_view = getMultiAdapter((self.context, self.request), name="plone")
        portal_workflow = getToolByName(self.context, "portal_workflow")
        portal_types = getToolByName(self.context, "portal_types")
        portal_membership = getToolByName(self.context, "portal_membership")
        registry = getUtility(IRegistry)
        use_view_action = registry.get("plone.types_use_view_action_in_listings", ())

        results = []
        if portal_membership.isAnonymousUser():
            worklist = []
        else:
            worklist = portal_workflow.getWorklistsResults()

        for i, obj in enumerate(worklist):
            if i % 2 == 0:
                table_row_class = "even"
            else:
                table_row_class = "odd"

            url = obj.absolute_url()
            path = "/".join(obj.getPhysicalPath())
            normalizer = getUtility(IIDNormalizer)
            type_class = "contenttype-" + normalizer.normalize(obj.portal_type)

            review_state = portal_workflow.getInfoFor(obj, "review_state", "")

            state_class = "state-" + normalizer.normalize(review_state)
            relative_url = portal_url.getRelativeContentURL(obj)

            type_title_msgid = portal_types[obj.portal_type].Title()
            url_href_title = "{}: {}".format(
                translate(type_title_msgid, context=self.request),
                safe_text(obj.Description()),
            )
            getMember = getToolByName(obj, "portal_membership").getMemberById
            creator_id = obj.Creator()
            creator = getMember(creator_id)
            if creator:
                creator_name = creator.getProperty("fullname", "") or creator_id
            else:
                creator_name = creator_id
            modified = "".join(
                map(
                    safe_text,
                    [
                        creator_name,
                        " - ",
                        plone_view.toLocalizedTime(
                            obj.ModificationDate(), long_format=1
                        ),
                    ],
                )
            )
            is_structural_folder = obj.restrictedTraverse(
                "@@plone_context_state"
            ).is_structural_folder()

            if obj.portal_type in use_view_action:
                view_url = url + "/view"
            elif is_structural_folder:
                view_url = url + "/folder_contents"
            else:
                view_url = url

            # Is this object the default page of its container?
            is_browser_default = is_default_page(aq_parent(aq_inner(obj)), obj)

            results.append(
                dict(
                    url=url,
                    url_href_title=url_href_title,
                    id=obj.getId(),
                    quoted_id=quote_plus(obj.getId()),
                    path=path,
                    title_or_id=obj.pretty_title_or_id(),
                    description=obj.Description(),
                    obj_type=obj.Type,
                    size=human_readable_size(obj.get_size()),
                    modified=modified,
                    type_class=type_class,
                    wf_state=review_state,
                    state_title=portal_workflow.getTitleForStateOnType(
                        review_state, obj.portal_type
                    ),
                    state_class=state_class,
                    is_browser_default=is_browser_default,
                    folderish=is_structural_folder,
                    relative_url=relative_url,
                    view_url=view_url,
                    table_row_class=table_row_class,
                    is_expired=is_expired(obj),
                )
            )
        return results

    @property
    def show_sort_column(self):
        return False

    def buttons(self):
        buttons = []
        portal_actions = getToolByName(self.context, "portal_actions")
        button_actions = portal_actions.listActionInfos(
            object=aq_inner(self.context), categories=("folder_buttons",)
        )

        for button in button_actions:
            # Make proper classes for our buttons
            if button["id"] != "paste" or self.context.cb_dataValid():
                buttons.append(self.setbuttonclass(button))
        return buttons

    def setbuttonclass(self, button):
        if button["id"] == "paste":
            button["cssclass"] = "btn btn-secondary"
        else:
            button["cssclass"] = "btn btn-primary"
        return button


class ReviewListBrowserView(TableBrowserView):
    table = ReviewListTable
