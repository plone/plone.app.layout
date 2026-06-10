from Acquisition import ImplicitAcquisitionWrapper
from lxml import etree
from lxml.etree import XMLSyntaxError
from plone.app.registry.exportimport.handler import RegistryExporter
from plone.app.registry.exportimport.handler import RegistryImporter
from plone.autoform.form import AutoExtensibleForm
from plone.base import PloneMessageFactory as _
from plone.base.batch import Batch
from plone.registry import field as registry_field
from plone.registry import Record
from plone.registry.interfaces import IRegistry
from plone.z3cform import layout
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.action import ActionErrorOccurred
from z3c.form.interfaces import WidgetActionExecutionError
from zope import schema
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.event import notify
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import Invalid
from zope.publisher.interfaces import IPublishTraverse
from zope.schema.vocabulary import SimpleVocabulary

import logging
import os
import re
import string

logger = logging.getLogger("plone.app.registry")


class RegistryEditForm(AutoExtensibleForm, form.EditForm):
    """Edit a records proxy based on an interface.

    To use this, you should use the <records /> element in a registry.xml
    GS import step to register records for a particular interface. Then
    subclass this form and set the 'schema' class variable to point to
    the same interface. You can use plone.autoform form hints to affect the
    rendering of the form, or override the update() method as appropriate.

    To get the standard control panel layout, use ControlPanelFormWrapper as
    the form wrapper, e.g.

        from plone.app.registry.browser.form import RegistryEditForm
        from plone.app.registry.browser.form import ControlPanelFormWrapper
        from my.package.interfaces import IMySettings
        form plone.z3cform import layout

        class MyForm(RegistryEditForm):
            schema = IMySettings

        MyFormView = layout.wrap_form(MyForm, ControlPanelFormWrapper)

    Then register MyFormView as a browser view.
    """

    control_panel_view = "@@overview-controlpanel"
    schema_prefix = None

    def getContent(self):
        return getUtility(IRegistry).forInterface(
            self.schema, prefix=self.schema_prefix
        )

    def updateActions(self):
        super().updateActions()
        self.actions["save"].addClass("btn btn-primary")
        self.actions["cancel"].addClass("btn btn-secondary")

    @button.buttonAndHandler(_("Save"), name="save")
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(_("Changes saved."), "info")
        self.request.response.redirect(self.request.getURL())

    @button.buttonAndHandler(_("Cancel"), name="cancel")
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_("Changes canceled."), "info")
        self.request.response.redirect(
            f"{getSite().absolute_url()}/{self.control_panel_view}"
        )


class ControlPanelFormWrapper(layout.FormWrapper):
    """Use this form as the plone.z3cform layout wrapper to get the control
    panel layout.
    """

    index = ViewPageTemplateFile("templates/registry_controlpanel_layout.pt")

    @property
    def control_panel_url(self):
        return f"{getSite().absolute_url()}/@@overview-controlpanel"


class RecordDeleteView(BrowserView):
    def __call__(self):
        if self.request.REQUEST_METHOD == "POST":
            name = self.request.form.get("name")
            if isinstance(name, list) and len(name) > 0:
                name = name[0]
            if self.request.form.get("form.buttons.delete"):
                if name in self.context:
                    del self.context.records[name]
                    messages = IStatusMessage(self.request)
                    messages.add("Successfully deleted field %s" % name, type="info")
            elif self.request.form.get("form.buttons.cancel") and name:
                messages = IStatusMessage(self.request)
                messages.add("Field %s was not deleted" % name, type="info")
            return self.request.response.redirect(self.context.absolute_url())
        return super().__call__()


class RecordEditForm(form.EditForm):
    """Edit a single record"""

    record = None

    @property
    def action(self):
        return f"{self.context.absolute_url()}/edit/{self.record.__name__}"

    def getContent(self):
        return ImplicitAcquisitionWrapper({"value": self.record.value}, self.context)

    def update(self):
        self.fields = field.Fields(
            self.record.field,
        )
        super().update()

    def updateActions(self):
        super().updateActions()
        self.actions["save"].addClass("btn btn-primary")
        self.actions["cancel"].addClass("btn btn-secondary")

    @property
    def label(self):
        return _("Edit record: ${name}", mapping={"name": self.record.__name__})

    @button.buttonAndHandler(_("Save"), name="save")
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.record.value = data["value"]
        IStatusMessage(self.request).addStatusMessage(_("Changes saved."), "info")
        self.request.response.redirect(self.context.absolute_url())

    @button.buttonAndHandler(_("Cancel"), name="cancel")
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_("Edit cancelled."), "info")
        self.request.response.redirect(self.context.absolute_url())


@implementer(IPublishTraverse)
class RecordEditView(layout.FormWrapper):
    form = RecordEditForm

    def __init__(self, context, request):
        super().__init__(context, request)
        self.request["disable_border"] = True

    def publishTraverse(self, request, name):
        path = self.request["TraversalRequestNameStack"] + [name]
        path.reverse()
        key = "/".join(path)
        del self.request["TraversalRequestNameStack"][:]
        record = self.context.records[key]
        self.record = record
        self.form_instance.record = record
        return self


_current_dir = os.path.dirname(__file__)


def _sort_first_lower(key):
    return key[0].lower()


class RegistryExporterView(BrowserView):
    """this view make sane exports of the registry.

    Main goal is to export in a way, that the output can be reused as
    best practice settings
    """

    template = ViewPageTemplateFile("templates/registry_exportxml.pt")

    def __call__(self):
        interface = self.request.form.get("interface", None)
        name = self.request.form.get("name", None)
        if not interface and not name:
            return self.template()
        return self.export(sinterface=interface, sname=name)

    def interfaces(self):
        prefixes = []
        registry = getUtility(IRegistry)
        baseurl = "{}/@@configuration_registry_export_xml?interface=".format(
            self.context.absolute_url()
        )
        for record in registry.records.values():
            if record.interfaceName is None:
                continue
            name = record.interfaceName
            url = f"{baseurl}{record.interfaceName}"
            pair = (name, url)
            if pair not in prefixes:
                prefixes.append(pair)

        return sorted(prefixes, key=_sort_first_lower)

    def prefixes(self):
        prefixes = []
        registry = getUtility(IRegistry)
        baseurl = "{}/@@configuration_registry_export_xml?".format(
            self.context.absolute_url()
        )
        for record in registry.records.values():
            if record.interfaceName == record.__name__:
                continue

            def add_split(part):
                url = f"{baseurl}name={part}"
                pair = (part, url)
                if pair not in prefixes:
                    prefixes.append(pair)
                if part.rfind("/") > part.rfind("."):
                    new_parts = part.rsplit("/", 1)
                else:
                    new_parts = part.rsplit(".", 1)
                if len(new_parts) > 1:
                    add_split(new_parts[0])

            add_split(record.__name__)
        return sorted(prefixes, key=_sort_first_lower)

    def export(self, sinterface=None, sname=None):
        registry = getUtility(IRegistry)
        root = etree.Element("registry")
        values = {}  # full prefix to valuerecord
        interface2values = {}
        interface2prefix = {}
        for record in registry.records.values():
            if sinterface and sinterface != record.interfaceName:
                continue
            if sname and not record.__name__.startswith(sname):
                continue
            prefix, value_key = record.__name__.rsplit(".", 1)
            xmlvalue = etree.Element("value")
            if record.value is None:
                continue
            if isinstance(record.value, (list, tuple)):
                for element in record.value:
                    xmlel = etree.SubElement(xmlvalue, "element")
                    xmlel.text = element
            elif isinstance(record.value, bool):
                xmlvalue.text = "True" if record.value else "False"
            elif isinstance(record.value, str):
                xmlvalue.text = record.value
            else:
                xmlvalue.text = str(record.value)

            if record.interfaceName:
                xmlvalue.attrib["key"] = value_key
                if record.interfaceName not in interface2values:
                    interface2values[record.interfaceName] = []
                interface2values[record.interfaceName].append(record.__name__)
                interface2prefix[record.interfaceName] = prefix
            values[record.__name__] = xmlvalue

        for ifname in sorted(interface2values):
            xmlrecord = etree.SubElement(root, "records")
            xmlrecord.attrib["interface"] = ifname
            xmlrecord.attrib["prefix"] = interface2prefix[ifname]
            for value in sorted(interface2values[ifname]):
                xmlrecord.append(values.pop(value))
        for name, xmlvalue in values.items():
            xmlrecord = etree.SubElement(root, "records")
            xmlrecord.attrib["prefix"] = name
            xmlrecord.append(xmlvalue)

        self.request.response.setHeader("Content-Type", "text/xml")
        filename = ""
        if sinterface:
            filename += sinterface
        if sinterface and sname:
            filename += "_-_"
        if sname:
            filename += sname
        self.request.response.setHeader(
            "Content-Disposition", f"attachment; filename={filename}.xml"
        )
        return etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )


def _true(s, v):
    return True


def _is_in(s, v):
    return s in v


def _starts_with(s, v):
    return v.startswith(s)


_okay_prefixes = ["Products", "plone.app", "plone"]


class FakeEnv:
    def getLogger(self, name):
        return logger

    def shouldPurge(self):
        return False


_valid_field_name_chars = string.ascii_letters + "._"


def checkFieldName(val):
    # Reuse same regex as in plone.registry.registry._Records to allow dottedname with one '/'
    validkey = re.compile(
        r"([a-zA-Z][a-zA-Z0-9_-]*)((?:\.[a-zA-Z0-9][a-zA-Z0-9_-]*)*)"
        r"([/][a-zA-Z0-9][a-zA-Z0-9_-]*)?((?:\.[a-zA-Z0-9][a-zA-Z0-9_-]*)*)$"
    ).match
    if not validkey(val):
        raise Invalid("Not a valid field name")
    return True


class IAddFieldForm(Interface):
    name = schema.TextLine(
        title=_("label_field_name", default="Field Name"),
        description='Must be in a format like "plone.my_name". Only letters, periods, underscores and up to one /.',
        required=True,
        constraint=checkFieldName,
    )

    title = schema.TextLine(
        title=_("label_field_title", default="Field Title"), required=True
    )

    field_type = schema.Choice(
        title="Field Type",
        vocabulary=SimpleVocabulary.fromValues(
            [
                "Bytes",
                "BytesLine",
                "ASCII",
                "ASCIILine",
                "Text",
                "TextLine",
                "Bool",
                "Int",
                "Float",
                "Decimal",
                "Password",
                "Datetime",
                "Date",
                "Timedelta",
                "SourceText",
                "URI",
                "Id",
                "DottedName",
                # XXX not supporting these types yet as it requires additional config
                # 'Tuple', 'List', 'Set', 'FrozenSet', 'Dict',
            ]
        ),
    )

    required = schema.Bool(title="Required", default=False)


class RecordsControlPanel(AutoExtensibleForm, form.Form):
    schema = IAddFieldForm
    ignoreContext = True
    submitted = False

    template = ViewPageTemplateFile("templates/registry_records.pt")

    @property
    def action(self):
        return f"{self.context.absolute_url()}#autotoc-item-autotoc-3"

    def updateActions(self):
        super().updateActions()
        self.actions["addfield"].addClass("btn-primary")

    @button.buttonAndHandler("Add field", name="addfield")
    def action_addfield(self, action):
        data, errors = self.extractData()
        self.submitted = True
        if not errors:
            field_class = getattr(registry_field, data["field_type"], None)
            if field_class is None:
                notify(
                    ActionErrorOccurred(
                        action,
                        WidgetActionExecutionError(
                            "field_type", Invalid("Invalid Field")
                        ),
                    )
                )
                return
            if data["name"] in self.context:
                notify(
                    ActionErrorOccurred(
                        action,
                        WidgetActionExecutionError(
                            "name", Invalid("Field name already in use")
                        ),
                    )
                )
                return

            new_field = field_class(title=data["title"], required=data["required"])
            new_record = Record(new_field)
            self.context.records[data["name"]] = new_record
            messages = IStatusMessage(self.request)
            messages.add("Successfully added field %s" % data["name"], type="info")
            return self.request.response.redirect(
                "{url}/edit/{field}".format(
                    url=self.context.absolute_url(), field=data["name"]
                )
            )

    def import_registry(self):
        try:
            fi = self.request.form["file"]
            body = fi.read()
        except (AttributeError, KeyError):
            messages = IStatusMessage(self.request)
            messages.add("Must provide XML file", type="error")
            body = None
        if body is not None:
            importer = RegistryImporter(self.context, FakeEnv())
            try:
                importer.importDocument(body)
            except XMLSyntaxError:
                messages = IStatusMessage(self.request)
                messages.add("Must provide valid XML file", type="error")
        return self.request.response.redirect(self.context.absolute_url())

    def export_registry(self):
        exporter = RegistryExporter(self.context, FakeEnv())
        body = exporter.exportDocument()
        resp = self.request.response
        resp.setHeader("Content-type", "text/xml")
        resp.setHeader("Content-Disposition", "attachment; filename=registry.xml")
        resp.setHeader("Content-Length", len(body))
        return body

    @property
    def control_panel_url(self):
        return f"{getSite().absolute_url()}/@@overview-controlpanel"

    def __call__(self):
        form = self.request.form
        if self.request.REQUEST_METHOD == "POST":
            if form.get("button.exportregistry"):
                return self.export_registry()
            if form.get("button.importregistry"):
                return self.import_registry()
        search = form.get("q")
        searchp = form.get("qp")
        compare = _is_in
        if searchp not in (None, ""):
            search = searchp
        if search is not None and search.startswith("prefix:"):
            search = search[len("prefix:") :]
            compare = _starts_with
        if not search:
            compare = _true

        self.prefixes = {}
        self.records = []
        for record in self.context.records.values():
            ifaceName = record.interfaceName
            if ifaceName is not None:
                recordPrefix = ifaceName.split(".")[-1]
                prefixValue = record.interfaceName
            else:
                prefixValue = record.__name__
                for prefix in _okay_prefixes:
                    name = record.__name__
                    if name.startswith(prefix):
                        recordPrefix = ".".join(
                            name.split(".")[: len(prefix.split(".")) + 1]
                        )
                        prefixValue = recordPrefix
                        break
            if recordPrefix not in self.prefixes:
                self.prefixes[recordPrefix] = prefixValue
            if compare(search, prefixValue) or compare(search, record.__name__):
                self.records.append(record)
        self.records = Batch(self.records, 15, int(form.get("b_start", "0")), orphan=1)
        return super().__call__()
