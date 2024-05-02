from zope.deferredimport import deprecated


deprecated(
    "Import INextPreviousProvider from plone.app.dexterity.behaviors.nextprevious instead (will be removed in Plone 7)",
    INextPreviousProvider="plone.app.dexterity.behaviors.nextprevious:INextPreviousProvider",
)
