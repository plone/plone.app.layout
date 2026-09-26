from Acquisition import aq_inner
from Products.Five.browser import BrowserView

import logging

logger = logging.getLogger(__name__)


class GetMacros(BrowserView):
    """Get macros.

    This is the former 'get_macros' python skin script.  It was moved
    to a browser view to avoid an Unauthorized exception when using
    five.pt.  Browser views are recommended anyway.
    """

    def get_macros(self, vdata):
        context = aq_inner(self.context)
        # We need to get the view appropriate for the object in the
        # history, not the current object, which may differ due to
        # some migration.
        type_info = context.portal_types.getTypeInfo(vdata.object)

        # build the name of special versions views
        if getattr(type_info, "getViewMethod", None) is not None:
            # Should use IBrowserDefault.getLayout ?
            def_method_name = type_info.getViewMethod(context)
        else:
            def_method_name = type_info.getActionInfo("object/view")["url"].split("/")[
                -1
            ] or getattr(type_info, "default_view", "view")
        versionPreviewMethodName = "version_%s" % def_method_name
        versionPreviewTemplate = getattr(context, versionPreviewMethodName, None)

        # check if a special version view exists
        if getattr(versionPreviewTemplate, "macros", None) is None:
            # Use the Plone's default view template
            versionPreviewTemplate = context.restrictedTraverse(def_method_name)

        if getattr(versionPreviewTemplate, "macros", None) is None:
            return None

        macro_names = ["content-core", "main"]

        try:
            return versionPreviewTemplate.macros["content-core"]
        except KeyError:
            pass  # No content-core macro could mean that we are in plone3 land
        try:
            return versionPreviewTemplate.macros["main"]
        except KeyError:
            logger.warn(
                'Missing TAL macros {} in template "{}".'.format(
                    ", ".join(macro_names), versionPreviewMethodName
                )
            )
