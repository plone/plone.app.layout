import zope.deferredimport


zope.deferredimport.initialize()
zope.deferredimport.deprecated(
    "Import from plone.app.dexterity instead (will be removed in Plone 7)",
    INextPreviousProvider="plone.app.dexterity.behaviors.nextprevious:INextPreviousProvider",
)
