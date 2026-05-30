from OFS.CopySupport import _cb_encode
from OFS.CopySupport import cookie_path
from OFS.Moniker import Moniker
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.interfaces import IStructureAction
from plone.base import PloneMessageFactory as _
from zope.i18n import translate
from zope.interface import implementer


@implementer(IStructureAction)
class CopyAction:
    order = 2

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_options(self):
        return {
            "tooltip": translate(_("Copy"), context=self.request),
            "id": "copy",
            "icon": "plone-copy",
            "url": self.context.absolute_url() + "/@@fc-copy",
        }


class CopyActionView(ContentsBaseAction):
    success_msg = _("Successfully copied items")
    failure_msg = _("Failed to copy items")

    def action(self, obj):
        self.oblist.append(obj)

    def finish(self):
        oblist = []
        for ob in self.oblist:
            if not ob.cb_isCopyable():
                self.errors.append(
                    _(
                        "${title} cannot be copied.",
                        mapping={"title": self.objectTitle(ob)},
                    )
                )
                continue
            m = Moniker(ob)
            oblist.append(m.dump())
        cp = (0, oblist)
        cp = _cb_encode(cp)
        resp = self.request.response
        resp.setCookie("__cp", cp, path="%s" % cookie_path(self.request))
        self.request["__cp"] = cp

    def __call__(self):
        self.oblist = []
        return super().__call__(keep_selection_order=True)
