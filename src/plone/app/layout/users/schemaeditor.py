from plone.app.users.browser.schemaeditor import ALLOWED_FIELDS
from plone.app.users.browser.schemaeditor import getFromBaseSchema
from plone.app.users.schema import IMemberSchemaContext
from plone.app.users.schema import IUserDataSchema
from plone.app.users.schema import SCHEMATA_KEY
from plone.base import PloneMessageFactory as _
from plone.schemaeditor.browser.schema.listing import SchemaListing
from plone.schemaeditor.browser.schema.traversal import SchemaContext
from plone.z3cform.layout import FormWrapper
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.interface import implementer


class SchemaListingPage(FormWrapper):
    form = SchemaListing
    index = ViewPageTemplateFile("schema_layout.pt")


@implementer(IMemberSchemaContext)
class MemberSchemaContext(SchemaContext):
    label = _("Edit Member Form Fields")

    def __init__(self, context, request):
        self.fieldsWhichCannotBeDeleted = ["fullname", "email"]
        self.showSaveDefaults = False
        self.enableFieldsets = False
        self.allowedFields = ALLOWED_FIELDS

        schema = getFromBaseSchema(IUserDataSchema)
        super().__init__(
            schema,
            request,
            name=SCHEMATA_KEY,
            title=_("Member Fields"),
        )
