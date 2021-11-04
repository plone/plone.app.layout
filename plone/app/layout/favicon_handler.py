from zope.component import adapter
from plone.registry.interfaces import IRecordModifiedEvent
from Products.CMFPlone.interfaces import ISiteSchema


@adapter(ISiteSchema, IRecordModifiedEvent)
def updateMimetype(settings, event=None):
    import pdb;
    pdb.set_trace()
    print('#')
    if event.record.fieldName != 'site_favicon':
        return

    filename, data = b64decode_file(event.newValue)
    mimetype = mimetypes.guess_type(filename)[0] if filename else 'image/x-icon'

    registry = getUtility(IRegistry)
    settings = registry.forInterface(ISiteSchema, prefix="plone")
    settings.site_favicon_mimetype = mimetype

