from DateTime import DateTime
from plone.app.layout.content.browser.contents import ContentsBaseAction
from plone.app.content.interfaces import IStructureAction
from plone.app.dexterity.behaviors.metadata import ICategorization
from plone.app.z3cform.widgets.datetime import get_date_options
from plone.base import PloneMessageFactory as _
from plone.base.defaultpage import check_default_page_via_view
from Products.CMFCore.interfaces._content import IFolderish
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory

import json


@implementer(IStructureAction)
class PropertiesAction:
    template = ViewPageTemplateFile("templates/properties.pt")
    order = 8

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_options(self):
        base_vocabulary = "%s/@@getVocabulary?name=" % getSite().absolute_url()
        return {
            "tooltip": translate(_("Properties"), context=self.request),
            "id": "properties",
            "icon": "plone-edit",
            "url": self.context.absolute_url() + "/@@fc-properties",
            "form": {
                "title": translate(
                    _("Modify properties on items"), context=self.request
                ),
                "template": self.template(
                    vocabulary_url="%splone.app.vocabularies.Users" % (base_vocabulary),
                    pattern_options=json.dumps(get_date_options(self.request)),
                ),
                "dataUrl": self.context.absolute_url() + "/@@fc-properties",
            },
        }


class PropertiesActionView(ContentsBaseAction):
    success_msg = _("Successfully updated metadata")
    failure_msg = _("Failure updating metadata")
    required_obj_permission = "Modify portal content"

    def __call__(self):
        if self.request.form.get("render") == "yes":
            lang_factory = getUtility(
                IVocabularyFactory, "plone.app.vocabularies.SupportedContentLanguages"
            )
            lang_vocabulary = lang_factory(self.context)
            languages = [
                {"title": term.title, "value": term.value} for term in lang_vocabulary
            ]
            return self.json(
                {
                    "languages": [
                        {
                            "title": translate(
                                _("label_no_change", default="No change"),
                                context=self.request,
                            ),
                            "value": "",
                        }
                    ]
                    + languages
                }
            )

        self.effectiveDate = self.request.form.get("effectiveDate")
        self.expirationDate = self.request.form.get("expirationDate")
        self.copyright = self.request.form.get("copyright")
        self.contributors = self.request.form.get("contributors")
        if self.contributors:
            self.contributors = self.contributors.split(",")
        else:
            self.contributors = []
        self.creators = self.request.form.get("creators", "")
        if self.creators:
            self.creators = self.creators.split(",")
        self.exclude = self.request.form.get("exclude-from-nav")
        self.language = self.request.form.get("language")
        self.recurse = self.request.form.get("recurse", "no") == "yes"
        return super().__call__()

    def action(self, obj, bypass_recurse=False):
        if check_default_page_via_view(obj, self.request):
            self.action(obj.aq_parent, bypass_recurse=True)
        recurse = self.recurse and not bypass_recurse
        if recurse and IFolderish.providedBy(obj):
            for sub in obj.values():
                self.action(sub)

        if self.effectiveDate and hasattr(obj, "effective_date"):
            obj.effective_date = DateTime(self.effectiveDate)
        if self.expirationDate and hasattr(obj, "expiration_date"):
            obj.expiration_date = DateTime(self.expirationDate)
        if self.copyright and hasattr(obj, "rights"):
            obj.rights = self.copyright
        if self.contributors and hasattr(obj, "contributors"):
            obj.contributors = tuple(self.contributors)
        if self.creators and hasattr(obj, "creators"):
            obj.creators = tuple(self.creators)
        if self.exclude and hasattr(obj, "exclude_from_nav"):
            obj.exclude_from_nav = self.exclude == "yes"

        behavior_categorization = ICategorization(obj)
        if self.language and behavior_categorization:
            behavior_categorization.language = self.language

        obj.reindexObject()
