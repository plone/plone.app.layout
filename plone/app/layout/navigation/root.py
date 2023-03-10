from zope.deferredimport import deprecated


deprecated(
    "Import from plone.base.navigationroot instead (will be removed in Plone 7)",
    getNavigationRoot="plone.base.navigationroot:get_navigation_root",
    getNavigationRootObject="plone.base.navigationroot:get_navigation_root_object",
)
