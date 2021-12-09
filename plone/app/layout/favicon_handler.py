from zope.component import adapter
from plone.registry.interfaces import IRecordModifiedEvent
from Products.CMFPlone.interfaces import ISiteSchema
from plone.formwidget.namedfile.converter import b64decode_file
import mimetypes
from zope.component import getUtility
from plone.registry.interfaces import IRegistry


from plone import api
import transaction


@adapter(ISiteSchema, IRecordModifiedEvent)
def updateMimetype(settings, event=None):
    # import pdb;
    # pdb.set_trace()

    if event.record.fieldName == 'site_favicon_mimetype':
        print('asdasdsadasdasdasdasdasdasd')

    if event.record.fieldName != 'site_favicon':
        return

    filename, data = b64decode_file(event.newValue)
    mimetype = mimetypes.guess_type(filename)[0] if filename else 'image/x-icon'

    # testing
    # dont save new value in registry ... why its only temp maybe no pointer?

    registry = getUtility(IRegistry)
    settings = registry.forInterface(ISiteSchema, prefix="plone")

    print('######### settings old')
    print(settings.site_favicon_mimetype)

    settings.site_favicon_mimetype = mimetype
    registry.records['plone.site_favicon_mimetype'].value = mimetype
    registry['plone.site_favicon_mimetype'] = mimetype
    api.portal.set_registry_record('plone.site_favicon_mimetype', mimetype)

    print('######### settings new')
    print(settings.site_favicon_mimetype)
    print('######### mimetype')
    print(mimetype)

    transaction.get().commit()
