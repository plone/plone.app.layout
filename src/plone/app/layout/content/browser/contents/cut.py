from OFS.CopySupport import _cb_encode
from OFS.CopySupport import cookie_path
from OFS.Moniker import Moniker
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.interfaces import IStructureAction
from plone.base import PloneMessageFactory as _
from plone.locking.interfaces import ILockable
from zope.i18n import translate
from zope.interface import implementer


@implementer(IStructureAction)
class CutAction:
    order = 1

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_options(self):
        return {
            "tooltip": translate(_("Cut"), context=self.request),
            "id": "cut",
            "icon": "plone-cut",
            "url": self.context.absolute_url() + "/@@fc-cut",
        }


class CutActionView(ContentsBaseAction):
    success_msg = _("Successfully cut items")
    failure_msg = _("Failed to cut items")

    def action(self, obj):
        self.oblist.append(obj)

    def finish(self):
        oblist = []
        for ob in self.oblist:
            try:
                lock_info = ob.restrictedTraverse("@@plone_lock_info")
            except AttributeError:
                lock_info = None
            if lock_info is not None:
                if lock_info.is_locked_for_current_user():
                    self.errors.append(
                        _(
                            "${title} is being edited and cannot be cut.",
                            mapping={"title": self.objectTitle(ob)},
                        )
                    )
                    continue
                elif lock_info.is_locked():
                    # unlock object as it is locked by current user
                    ILockable(ob).unlock()

            if not ob.cb_isMoveable():
                self.errors.append(
                    _(
                        "${title} is being edited and cannot be cut.",
                        mapping={"title": self.objectTitle(ob)},
                    )
                )
                continue
            m = Moniker(ob)
            oblist.append(m.dump())
        cp = (1, oblist)
        cp = _cb_encode(cp)
        resp = self.request.response
        resp.setCookie("__cp", cp, path="%s" % cookie_path(self.request))
        self.request["__cp"] = cp

    def __call__(self):
        self.oblist = []
        return super().__call__()
