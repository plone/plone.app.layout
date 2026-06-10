from lxml import etree
from OFS.ObjectManager import ObjectManager
from plone.app.registry import Registry
from plone.app.registry.exportimport.handler import exportRegistry
from plone.app.registry.exportimport.handler import importRegistry
from plone.app.registry.tests import data
from plone.registry import field
from plone.registry import FieldRef
from plone.registry import Record
from plone.registry.interfaces import IFieldRef
from plone.registry.interfaces import IInterfaceAwareRecord
from plone.registry.interfaces import IRegistry
from plone.supermodel.utils import prettyXML
from plone.testing import zca
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import (
    DummyImportContext as BaseDummyImportContext,
)
from zope.component import provideUtility
from zope.configuration import xmlconfig
from zope.interface import alsoProvides

import unittest

configuration = """\
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:meta="http://namespaces.zope.org/meta">
    <meta:provides feature="plone" />
    <include package="zope.component" file="meta.zcml" />
    <include package="plone.registry" />
    <include package="plone.app.registry.exportimport" file="handlers.zcml" />
</configure>
"""


class DummyImportContext(BaseDummyImportContext):
    _directories = {}

    def listDirectory(self, path):
        return self._directories.get(path, [])

    def isDirectory(self, path):
        return path in self._directories


class ExportImportTest(unittest.TestCase):
    layer = zca.UNIT_TESTING

    def setUp(self):
        self.site = ObjectManager("plone")
        self.registry = Registry("portal_registry")
        provideUtility(provides=IRegistry, component=self.registry)
        context = xmlconfig.string(configuration, execute=True)
        try:
            import Zope2.App.zcml

            self._context = Zope2.App.zcml._context
            Zope2.App.zcml._context = context
        except ImportError:
            pass

    def tearDown(self):
        try:
            import Zope2.App.zcml

            Zope2.App.zcml._context = self._context
        except ImportError:
            pass

    def assertXmlEquals(self, expected, actual):
        expected_tree = etree.XML(expected)
        actual_tree = etree.XML(actual)

        if etree.tostring(expected_tree) != etree.tostring(actual_tree):
            print()
            print("Expected:")
            print(prettyXML(expected_tree))
            print()

            print()
            print("Actual:")
            print(prettyXML(actual_tree))
            print()

            raise AssertionError("XML mismatch")


class TestImport(ExportImportTest):
    def test_empty_import_no_purge(self):
        xml = "<registry/>"
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))

    def test_import_purge(self):
        xml = "<registry/>"
        context = DummyImportContext(self.site, purge=True)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(0, len(self.registry.records))

    def test_import_records(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(3, len(self.registry.records))

        self.assertIn("plone.app.registry.tests.data.ITestSettings.name", self.registry)
        self.assertIn("plone.app.registry.tests.data.ITestSettings.age", self.registry)

    def test_import_records_disallowed(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettingsDisallowed" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        try:
            importRegistry(context)
        except TypeError:
            pass
        else:
            self.fail()

    def test_import_records_omit(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettingsDisallowed">
        <omit>blob</omit>
    </records>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(3, len(self.registry.records))

        self.assertIn(
            "plone.app.registry.tests.data.ITestSettingsDisallowed.name", self.registry
        )
        self.assertIn(
            "plone.app.registry.tests.data.ITestSettingsDisallowed.age", self.registry
        )

    def test_import_records_remove(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))
        delete_xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" remove="true"/>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": delete_xml}

        importRegistry(context)

        self.assertEqual(0, len(self.registry.records))

    def test_import_records_delete_deprecated(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))
        delete_xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" delete="true"/>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": delete_xml}

        importRegistry(context)

        self.assertEqual(0, len(self.registry.records))

    def test_import_records_remove_with_omit(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))
        delete_xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" remove="true">
      <omit>name</omit>
    </records>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": delete_xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))

        self.assertIn("plone.app.registry.tests.data.ITestSettings.name", self.registry)
        self.assertNotIn(
            "plone.app.registry.tests.data.ITestSettings.age", self.registry
        )

    def test_import_records_remove_with_value(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))
        delete_xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" remove="true">
      <value key="name">Spam</value>
    </records>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": delete_xml}

        self.assertRaises(ValueError, importRegistry, context)

        self.assertEqual(2, len(self.registry.records))

    def test_import_records_with_prefix(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" prefix="plone.app.registry.tests.data.SomethingElse" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))

        self.assertIn("plone.app.registry.tests.data.SomethingElse.name", self.registry)
        self.assertIn("plone.app.registry.tests.data.SomethingElse.age", self.registry)

    def test_import_records_with_values(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" prefix="plone.app.registry.tests.data.SomethingElse">
        <value key="name">Magic</value>
        <value key="age">42</value>
    </records>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))

        self.assertIn("plone.app.registry.tests.data.SomethingElse.name", self.registry)
        self.assertIn("plone.app.registry.tests.data.SomethingElse.age", self.registry)

        self.assertEqual(
            self.registry["plone.app.registry.tests.data.SomethingElse.name"], "Magic"
        )
        self.assertEqual(
            self.registry["plone.app.registry.tests.data.SomethingElse.age"], 42
        )

    def test_import_records_nonexistant_interface(self):
        xml = """\
<registry>
    <records interface="non.existent.ISchema" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.assertRaises(ImportError, importRegistry, context)

    def test_import_records_nonexistant_interface_condition_not_installed(self):
        xml = """\
<registry>
    <records interface="non.existent.ISchema"
             condition="not-installed non" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.assertRaises(ImportError, importRegistry, context)

    def test_import_value_only(self):
        xml = """\
<registry>
    <record name="test.export.simple">
        <value>Imported value</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Simple record", self.registry.records["test.export.simple"].field.title
        )
        self.assertEqual("Imported value", self.registry["test.export.simple"])

    def test_import_value_only_condition_installed(self):
        xml = """\
<registry>
    <record name="test.export.simple"
            condition="installed non">
        <value>Imported value</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Simple record", self.registry.records["test.export.simple"].field.title
        )
        self.assertEqual("Sample value", self.registry["test.export.simple"])

    def test_import_value_only_condition_have(self):
        xml = """\
<registry>
    <record name="test.export.simple"
            condition="have plone">
        <value>Imported value</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Simple record", self.registry.records["test.export.simple"].field.title
        )
        self.assertEqual("Imported value", self.registry["test.export.simple"])

    def test_import_value_only_condition_not_have(self):
        xml = """\
<registry>
    <record name="test.export.simple"
            condition="not-have plone">
        <value>Imported value</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Simple record", self.registry.records["test.export.simple"].field.title
        )
        self.assertEqual("Sample value", self.registry["test.export.simple"])

    def test_import_interface_and_value(self):
        xml = """\
<registry>
    <record interface="plone.app.registry.tests.data.ITestSettingsDisallowed" field="age">
        <value>2</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Age",
            self.registry.records[
                "plone.app.registry.tests.data.ITestSettingsDisallowed.age"
            ].field.title,
        )
        self.assertEqual(
            2,
            self.registry["plone.app.registry.tests.data.ITestSettingsDisallowed.age"],
        )

    def test_import_interface_with_differnet_name(self):
        xml = """\
<registry>
    <record name="plone.registry.oops" interface="plone.app.registry.tests.data.ITestSettingsDisallowed" field="age">
        <value>2</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Age", self.registry.records["plone.registry.oops"].field.title
        )
        self.assertEqual(2, self.registry["plone.registry.oops"])

    def test_import_interface_no_value(self):
        xml = """\
<registry>
    <record interface="plone.app.registry.tests.data.ITestSettingsDisallowed" field="name" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Name",
            self.registry.records[
                "plone.app.registry.tests.data.ITestSettingsDisallowed.name"
            ].field.title,
        )
        self.assertEqual(
            "Mr. Registry",
            self.registry["plone.app.registry.tests.data.ITestSettingsDisallowed.name"],
        )

    def test_import_field_only(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.TextLine">
          <default>N/A</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.TextLine
            )
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(
            "value", self.registry.records["test.registry.field"].field.__name__
        )
        self.assertEqual("N/A", self.registry["test.registry.field"])

    def test_import_field_ref(self):
        xml = """\
<registry>
    <record name="test.registry.field.override">
        <field ref="test.registry.field" />
        <value>Another value</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        importRegistry(context)

        self.assertEqual(2, len(self.registry.records))
        self.assertTrue(
            IFieldRef.providedBy(
                self.registry.records["test.registry.field.override"].field
            )
        )
        self.assertEqual(
            "Simple record",
            self.registry.records["test.registry.field.override"].field.title,
        )
        self.assertEqual(
            "value",
            self.registry.records["test.registry.field.override"].field.__name__,
        )
        self.assertEqual("Another value", self.registry["test.registry.field.override"])

    def test_import_field_and_interface(self):
        xml = """\
<registry>
    <record name="test.registry.field" interface="plone.app.registry.tests.data.ITestSettingsDisallowed" field="age">
        <field type="plone.registry.field.ASCIILine">
          <default>N/A</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.ASCIILine
            )
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual("N/A", self.registry["test.registry.field"])

    def test_import_overwrite_field_with_field(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.ASCIILine">
          <default>Nada</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"), value="Old value"
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.ASCIILine
            )
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual("Nada", self.registry["test.registry.field"])

    def test_import_overwrite_field_with_interface(self):
        xml = """\
<registry>
    <record name="test.registry.field"  interface="plone.app.registry.tests.data.ITestSettingsDisallowed" field="age" />
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"), value="Old value"
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Int)
        )
        self.assertEqual(
            "Age", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(None, self.registry["test.registry.field"])

    def test_import_collection_field(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.FrozenSet">
          <title>Simple record</title>
          <default>
            <element>1</element>
            <element>3</element>
          </default>
          <value_type type="plone.registry.field.Int">
            <title>Value</title>
          </value_type>
        </field>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"), value="Old value"
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.FrozenSet
            )
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(frozenset([1, 3]), self.registry["test.registry.field"])

    def test_import_collection_value(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value>
            <element>4</element>
            <element>6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Set(title="Simple record", value_type=field.Int(title="Val")),
            value={1},
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Set)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(frozenset([4, 6]), self.registry["test.registry.field"])

    def test_import_collection_nopurge(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element>4</element>
            <element>6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Set(title="Simple record", value_type=field.Int(title="Val")),
            value={1},
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Set)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(frozenset([1, 4, 6]), self.registry["test.registry.field"])

    def test_import_collection_list_append(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element>4</element>
            <element>6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.List(title="Simple record", value_type=field.Int(title="Val")),
            value=[2, 4],
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual([2, 4, 6], self.registry["test.registry.field"])

    def test_import_collection_tuple_append(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element>b</element>
            <element>c</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Tuple(title="Simple record", value_type=field.TextLine(title="Val")),
            value=(
                "a",
                "b",
            ),
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            (
                "a",
                "b",
                "c",
            ),
            self.registry["test.registry.field"],
        )

    def test_import_collection_set_append(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element>4</element>
            <element>6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Set(title="Simple record", value_type=field.Int(title="Val")),
            value={2, 4},
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual({2, 4, 6}, self.registry["test.registry.field"])

    def test_import_collection_frozenset_append(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element>4</element>
            <element>6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.FrozenSet(title="Simple record", value_type=field.Int(title="Val")),
            value=frozenset([2, 4]),
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(frozenset([2, 4, 6]), self.registry["test.registry.field"])

    def test_import_dict_field(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.Dict">
          <title>Simple record</title>
          <default>
            <element key="a">1</element>
            <element key="b">3</element>
          </default>
          <key_type type="plone.registry.field.ASCIILine">
            <title>Key</title>
          </key_type>
          <value_type type="plone.registry.field.Int">
            <title>Value</title>
          </value_type>
        </field>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"), value="Old value"
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Dict)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual({"a": 1, "b": 3}, self.registry["test.registry.field"])

    def test_import_dict_value(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value>
            <element key="x">4</element>
            <element key="y">6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Dict(
                title="Simple record",
                key_type=field.ASCIILine(title="Key"),
                value_type=field.Int(title="Val"),
            ),
            value={"a": 1},
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Dict)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual({"x": 4, "y": 6}, self.registry["test.registry.field"])

    def test_import_dict_nopurge(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <value purge="false">
            <element key="x">4</element>
            <element key="y">6</element>
        </value>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.Dict(
                title="Simple record",
                key_type=field.ASCIILine(title="Key"),
                value_type=field.Int(title="Val"),
            ),
            value={"a": 1},
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Dict)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual({"a": 1, "x": 4, "y": 6}, self.registry["test.registry.field"])

    def test_import_choice_field(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.Choice">
          <title>Simple record</title>
          <values>
            <element>One</element>
            <element>Two</element>
          </values>
        </field>
    </record>
</registry>
"""

        self.registry.records["test.registry.field"] = Record(
            field.TextLine(title="Simple record", default="N/A"), value="Old value"
        )

        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(self.registry.records["test.registry.field"].field, field.Choice)
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(
            ["One", "Two"],
            [
                t.value
                for t in self.registry.records["test.registry.field"].field.vocabulary
            ],
        )
        self.assertEqual(None, self.registry["test.registry.field"])

    def test_import_with_comments(self):
        xml = """\
<registry>
    <records interface="plone.app.registry.tests.data.ITestSettings" prefix="plone.app.registry.tests.data.SomethingElse">
        <!-- set values in this interface -->
        <value key="name">Magic</value>
        <value key="age">42</value>
    </records>
    <record name="test.registry.field">
        <!-- comment on this field or value -->
        <field type="plone.registry.field.TextLine">
          <default>N/A</default>
          <!-- comment here too -->
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(3, len(self.registry.records))

        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.TextLine
            )
        )
        self.assertEqual(
            "Simple record", self.registry.records["test.registry.field"].field.title
        )
        self.assertEqual(
            "value", self.registry.records["test.registry.field"].field.__name__
        )
        self.assertEqual("N/A", self.registry["test.registry.field"])

        self.assertIn("plone.app.registry.tests.data.SomethingElse.name", self.registry)
        self.assertIn("plone.app.registry.tests.data.SomethingElse.age", self.registry)
        self.assertEqual(
            self.registry["plone.app.registry.tests.data.SomethingElse.name"], "Magic"
        )
        self.assertEqual(
            self.registry["plone.app.registry.tests.data.SomethingElse.age"], 42
        )

    def test_remove(self):
        xml = """\
<registry>
    <record name="test.export.simple" remove="true" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(0, len(self.registry.records))

    def test_delete_deprecated(self):
        xml = """\
<registry>
    <record name="test.export.simple" delete="true" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(0, len(self.registry.records))

    def test_delete_not_found(self):
        xml = """\
<registry>
    <record name="test.export.bogus" remove="true" />
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )
        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertEqual(
            "Simple record", self.registry.records["test.export.simple"].field.title
        )
        self.assertEqual("Sample value", self.registry["test.export.simple"])

    def test_import_folder(self):
        xml1 = """\
<registry>
    <record name="test.registry.foobar1">
        <field type="plone.registry.field.TextLine">
          <default>N/A</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        xml2 = """\
<registry>
    <record name="test.registry.foobar2">
        <field type="plone.registry.field.TextLine">
          <default>N/A</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        xml3 = """\
<registry>
    <record name="test.registry.foobar3">
        <field type="plone.registry.field.TextLine">
          <default>N/A</default>
          <title>Simple record</title>
        </field>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {
            "registry.xml": xml1,
            ".ignored_file": "",
            "registry/foo2.xml": xml2,
            "registry/foo3.xml": xml3,
        }
        context._directories = {
            "registry": [
                "foo2.xml",
                "foo3.xml",
                ".ignored_file",
            ]
        }
        importRegistry(context)

        self.assertEqual(3, len(self.registry.records))

        for idx in range(1, 4):
            fieldname = "test.registry.foobar%i" % idx
            self.assertTrue(
                isinstance(self.registry.records[fieldname].field, field.TextLine)
            )
            self.assertEqual(
                "Simple record", self.registry.records[fieldname].field.title
            )
            self.assertEqual("value", self.registry.records[fieldname].field.__name__)
            self.assertEqual("N/A", self.registry[fieldname])

    def test_import_jsonfield_only(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.JSONField">
          <default>{}</default>
          <title>JSON record</title>
        </field>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.JSONField
            )
        )
        self.assertEqual(
            "JSON record", self.registry.records["test.registry.field"].field.title
        )
        self.assertDictEqual({}, self.registry["test.registry.field"])

    def test_import_jsonfield_with_value(self):
        xml = """\
<registry>
    <record name="test.registry.field">
        <field type="plone.registry.field.JSONField">
          <default>{}</default>
          <title>JSON record</title>
        </field>
        <value>{"items":[{"color":"red","value":"one"},{"color":"röd","value":"two"}]}</value>
    </record>
</registry>
"""
        context = DummyImportContext(self.site, purge=False)
        context._files = {"registry.xml": xml}

        importRegistry(context)

        self.assertEqual(1, len(self.registry.records))
        self.assertTrue(
            isinstance(
                self.registry.records["test.registry.field"].field, field.JSONField
            )
        )
        self.assertEqual(
            "JSON record", self.registry.records["test.registry.field"].field.title
        )
        self.assertDictEqual(
            {
                "items": [
                    {"color": "red", "value": "one"},
                    {"color": "röd", "value": "two"},
                ]
            },
            self.registry["test.registry.field"],
        )


class TestExport(ExportImportTest):
    def test_export_empty(self):
        xml = """<registry />"""
        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_simple(self):
        xml = """\
<registry>
  <record name="test.export.simple">
    <field type="plone.registry.field.TextLine">
      <default>N/A</default>
      <title>Simple record</title>
    </field>
    <value>Sample value</value>
  </record>
</registry>"""

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_interface(self):
        xml = """\
<registry>
  <record name="plone.app.registry.tests.data.ITestSettings.age" interface="plone.app.registry.tests.data.ITestSettings" field="age">
    <field type="plone.registry.field.Int">
      <min>0</min>
      <title>Age</title>
    </field>
    <value />
  </record>
  <record name="plone.app.registry.tests.data.ITestSettings.name" interface="plone.app.registry.tests.data.ITestSettings" field="name">
    <field type="plone.registry.field.TextLine">
      <default>Mr. Registry</default>
      <title>Name</title>
    </field>
    <value>Mr. Registry</value>
  </record>
  <record name="test.export.simple">
    <field type="plone.registry.field.TextLine">
      <default>N/A</default>
      <title>Simple record</title>
    </field>
    <value>Sample value</value>
  </record>
</registry>"""

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        self.registry.registerInterface(data.ITestSettings)

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_field_ref(self):
        xml = """\
<registry>
  <record name="test.export.simple">
    <field type="plone.registry.field.TextLine">
      <default>N/A</default>
      <title>Simple record</title>
    </field>
    <value>Sample value</value>
  </record>
  <record name="test.export.simple.override">
    <field ref="test.export.simple" />
    <value>Another value</value>
  </record>
</registry>"""

        self.registry.records["test.export.simple"] = refRecord = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        self.registry.records["test.export.simple.override"] = Record(
            FieldRef(refRecord.__name__, refRecord.field), value="Another value"
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_collection(self):
        xml = """\
<registry>
  <record name="test.export.simple">
    <field type="plone.registry.field.List">
      <title>Simple record</title>
      <value_type type="plone.registry.field.Int">
        <title>Val</title>
      </value_type>
    </field>
    <value>
      <element>2</element>
    </value>
  </record>
</registry>"""
        self.registry.records["test.export.simple"] = Record(
            field.List(title="Simple record", value_type=field.Int(title="Val")),
            value=[2],
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_dict(self):
        xml = """\
<registry>
  <record name="test.export.dict">
    <field type="plone.registry.field.Dict">
      <default />
      <key_type type="plone.registry.field.ASCIILine">
        <title>Key</title>
      </key_type>
      <title>Dict</title>
      <value_type type="plone.registry.field.Int">
        <title>Value</title>
      </value_type>
    </field>
    <value>
      <element key="a">1</element>
    </value>
  </record>
</registry>"""

        self.registry.records["test.export.dict"] = Record(
            field.Dict(
                title="Dict",
                default={},
                key_type=field.ASCIILine(title="Key"),
                value_type=field.Int(title="Value"),
            ),
            value={"a": 1},
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_choice(self):
        xml = """\
<registry>
  <record name="test.export.choice">
    <field type="plone.registry.field.Choice">
      <title>Simple record</title>
      <vocabulary>dummy.vocab</vocabulary>
    </field>
    <value />
  </record>
</registry>"""

        self.registry.records["test.export.choice"] = Record(
            field.Choice(title="Simple record", vocabulary="dummy.vocab")
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_missing_schema_does_not_error(self):
        xml = """\
<registry>
  <record name="test.export.simple" interface="non.existent.ISchema" field="blah">
    <field type="plone.registry.field.TextLine">
      <default>N/A</default>
      <title>Simple record</title>
    </field>
    <value>Sample value</value>
  </record>
</registry>"""

        self.registry.records["test.export.simple"] = Record(
            field.TextLine(title="Simple record", default="N/A"),
            value="Sample value",
        )

        # Note: These are nominally read-only!
        self.registry.records["test.export.simple"].field.interfaceName = (
            "non.existent.ISchema"
        )
        self.registry.records["test.export.simple"].field.fieldName = "blah"

        alsoProvides(self.registry.records["test.export.simple"], IInterfaceAwareRecord)

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])

    def test_export_with_jsonfield(self):
        xml = """\
<registry>
  <record name="test.export.field">
    <field type="plone.registry.field.JSONField">
      <default>{}</default>
      <title>Dict</title>
    </field>
    <value>{'items': [{'color': 'red', 'value': 'one'}, {'color': 'röd', 'value': 'two'}]}</value>
  </record>
</registry>"""

        self.registry.records["test.export.field"] = Record(
            field.JSONField(
                title="Dict",
                default={},
            ),
            value={
                "items": [
                    {"color": "red", "value": "one"},
                    {"color": "röd", "value": "two"},
                ]
            },
        )

        context = DummyExportContext(self.site)
        exportRegistry(context)

        self.assertEqual("registry.xml", context._wrote[0][0])
        self.assertXmlEquals(xml, context._wrote[0][1])
