from plone.autoform.form import AutoExtensibleForm
from plone.base.interfaces import ISelectableConstrainTypes
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form import button
from z3c.form import form
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.i18nmessageid import MessageFactory
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import invariant
from zope.interface.exceptions import Invalid
from zope.schema import Choice
from zope.schema import List
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

# XXX
# acquire locallyAllowedTypes from parent (default)
ACQUIRE = -1

# use default behavior of PortalFolder which uses the FTI information
DISABLED = 0

# allow types from locallyAllowedTypes only
ENABLED = 1


def ST(key, title):
    return SimpleTerm(value=key, title=title)


# reuse the translations that we had in atcontenttypes
_ = MessageFactory("plone")

possible_constrain_types = SimpleVocabulary(
    [
        ST(
            ACQUIRE,
            _("constraintypes_acquire_label", default="Use parent folder settings"),
        ),
        ST(DISABLED, _("constraintypes_disable_label", default="Use portal default")),
        ST(ENABLED, _("constraintypes_enable_label", default="Select manually")),
    ]
)


@implementer(IVocabularyFactory)
class ValidTypes:
    def __call__(self, context):
        constrain_aspect = context.context
        request = getRequest()
        items = []
        for type_ in constrain_aspect.getDefaultAddableTypes():
            items.append(SimpleTerm(value=type_.getId(), title=type_.Title()))

        return SimpleVocabulary(
            sorted(items, key=lambda x: translate(x.title, context=request).lower())
        )


ValidTypesFactory = ValidTypes()


class IConstrainForm(Interface):
    constrain_types_mode = Choice(
        title=_("label_type_restrictions", default="Type restrictions"),
        description=_(
            "help_add_restriction_mode",
            default="Select the restriction policy " "in this location",
        ),
        vocabulary=possible_constrain_types,
        required=True,
        default=ACQUIRE,
    )

    allowed_types = List(
        title=_("label_immediately_addable_types", default="Allowed types"),
        description=_(
            "help_immediately_addable_types",
            default="Controls what types are addable " "in this location",
        ),
        value_type=Choice(source="plone.app.content.ValidAddableTypes"),
        required=False,
    )

    secondary_types = List(
        title=_("label_locally_allowed_types", default="Secondary types"),
        description=_(
            "help_locally_allowed_types",
            default=""
            "Select which types should be available in the "
            "'More&hellip;' submenu <em>instead</em> of in the "
            "main pulldown. "
            "This is useful to indicate that these are not the "
            "preferred types "
            "in this location, but are allowed if you really "
            "need them.",
        ),
        value_type=Choice(source="plone.app.content.ValidAddableTypes"),
        required=False,
    )

    @invariant
    def legal_not_immediately_addable(data):
        missing = []
        for one_allowed in data.secondary_types:
            if one_allowed not in data.allowed_types:
                missing.append(one_allowed)
        if missing:
            raise Invalid(
                _(
                    "You cannot have a type as a secondary type without "
                    "having it allowed. You have selected ${types}.",
                    mapping=dict(types=", ".join(missing)),
                )
            )
        return True


@implementer(IConstrainForm)
class FormContentAdapter:
    def __init__(self, context):
        self.context = ISelectableConstrainTypes(context)

    @property
    def constrain_types_mode(self):
        return self.context.getConstrainTypesMode()

    @property
    def allowed_types(self):
        return self.context.getLocallyAllowedTypes()

    @property
    def secondary_types(self):
        immediately_addable = self.context.getImmediatelyAddableTypes()
        return [
            t
            for t in self.context.getLocallyAllowedTypes()
            if t not in immediately_addable
        ]


class ConstrainsFormView(AutoExtensibleForm, form.EditForm):
    schema = IConstrainForm
    label = _(
        "heading_set_content_type_restrictions",
        default="Restrict what types of content can be added",
    )
    template = ViewPageTemplateFile("constraintypes.pt")

    def getContent(self):
        return FormContentAdapter(self.context)

    def updateFields(self):
        super().updateFields()
        self.fields["allowed_types"].widgetFactory = CheckBoxFieldWidget
        self.fields["secondary_types"].widgetFactory = CheckBoxFieldWidget

    def updateWidgets(self):
        super().updateWidgets()
        self.widgets["allowed_types"].addClass("current_prefer_form")
        self.widgets["secondary_types"].addClass("current_allow_form")
        self.widgets["constrain_types_mode"].addClass("constrain_types_mode_form")

    def updateActions(self):
        super().updateActions()
        self.actions["save"].addClass("btn btn-primary")

    @button.buttonAndHandler(_("label_save", default="Save"), name="save")
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        allowed_types = data["allowed_types"]
        immediately_addable = [
            t for t in allowed_types if t not in data["secondary_types"]
        ]

        aspect = ISelectableConstrainTypes(self.context)
        aspect.setConstrainTypesMode(data["constrain_types_mode"])
        aspect.setLocallyAllowedTypes(allowed_types)
        aspect.setImmediatelyAddableTypes(immediately_addable)
        contextURL = self.context.absolute_url()
        self.request.response.redirect(contextURL)

    @button.buttonAndHandler(_("label_cancel", default="Cancel"), name="cancel")
    def handleCancel(self, action):
        contextURL = self.context.absolute_url()
        self.request.response.redirect(contextURL)
