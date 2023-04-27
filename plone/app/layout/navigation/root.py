from zope.deferredimport import deprecated


deprecated(
    "Import as get_navigation_root from plone.base.navigationroot instead (will be removed in Plone 7)",
    getNavigationRoot="plone.base.navigationroot:get_navigation_root",
)
deprecated(
    "Import as get_navigation_root_object from plone.base.navigationroot instead (will be removed in Plone 7)",
    getNavigationRootObject="plone.base.navigationroot:get_navigation_root_object",
)
