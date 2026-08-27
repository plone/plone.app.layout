from AccessControl import Unauthorized
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.interfaces import IStructureAction
from plone.base import PloneMessageFactory as _
from ZODB.POSException import ConflictError
from zope.i18n import translate
from zope.interface import implementer


@implementer(IStructureAction)
class PasteAction:
    order = 3

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_options(self):
        return {
            "tooltip": translate(_("Paste"), context=self.request),
            "id": "paste",
            "icon": "plone-paste",
            "url": self.context.absolute_url() + "/@@fc-paste",
        }


class PasteActionView(ContentsBaseAction):
    required_obj_permission = "Copy or Move"
    success_msg = _("Successfully pasted items")
    failure_msg = _("Failed to paste items")

    def __call__(self):
        self.protect()
        self.errors = []

        parts = str(self.request.form["folder"].lstrip("/")).split("/")
        parent = self.site.unrestrictedTraverse("/".join(parts[:-1]))
        self.dest = parent.restrictedTraverse(parts[-1])

        try:
            self.dest.manage_pasteObjects(self.request["__cp"])
        except ConflictError:
            raise
        except Unauthorized:
            # avoid this unfriendly exception text:
            # "You are not allowed to access 'manage_pasteObjects' in this
            # context"
            self.errors.append(
                _(
                    "You are not authorized to paste ${title} here.",
                    mapping={"title": self.objectTitle(self.dest)},
                )
            )
        except ValueError as e:
            if "Disallowed subobject type: " in e.args[0]:
                msg_parts = e.args[0].split(":")
                self.errors.append(
                    _(
                        'Disallowed subobject type "${type}"',
                        mapping={"type": msg_parts[1].strip()},
                    )
                )
            else:
                raise e

        return self.message()
