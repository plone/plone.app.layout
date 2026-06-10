from plone.app.layout.controlpanels.registry import ControlPanelFormWrapper
from plone.app.layout.controlpanels.registry import RecordDeleteView
from plone.app.layout.controlpanels.registry import RecordsControlPanel
from plone.app.layout.testing import PLONE_APP_LAYOUT_INTEGRATION_TESTING
from plone.registry import Record
from plone.registry.field import TextLine
from zope.component import getMultiAdapter

import unittest


class TestRegistryBaseControlpanel(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def test_registry_base_controlpanel__control_panel_url(self):
        """Test, if control_panel_url property of the base controlpanel returns
        the correct url.
        """
        view = ControlPanelFormWrapper(None, None)
        self.assertEqual(
            view.control_panel_url, "http://nohost/plone/@@overview-controlpanel"
        )


class TestRecordsControlPanel(unittest.TestCase):
    layer = PLONE_APP_LAYOUT_INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]
        self.portal = self.layer["portal"]

    def test_records_control_panel__control_panel_url(self):
        """Test, if control_panel_url property of the registry controlpanel
        returns the correct url.
        """
        view = RecordsControlPanel(None, None)
        self.assertEqual(
            view.control_panel_url, "http://nohost/plone/@@overview-controlpanel"
        )

    def test_add_new_record(self):
        self.request.form.update(
            {
                "form.widgets.name": "foobar",
                "form.widgets.title": "Foobar",
                "form.widgets.field_type": "TextLine",
                "form.widgets.required-empty-marker": "1",
                "form.buttons.addfield": "Add field",
            }
        )

        registry = self.portal.portal_registry

        view = RecordsControlPanel(registry, self.request)
        view.update()

        data, errors = view.extractData()
        self.assertTrue(len(errors) == 0)

        view.action_addfield(view, None)
        self.assertTrue("foobar" in registry.records)

    def test_delete(self):
        registry = self.portal.portal_registry
        new_field = TextLine()
        new_record = Record(new_field)
        registry.records["foobar"] = new_record
        self.assertTrue("foobar" in registry.records)

        self.request.form.update({"form.buttons.delete": "Yes", "name": "foobar"})
        self.request.REQUEST_METHOD = "POST"
        view = RecordDeleteView(registry, self.request)
        view()
        self.assertTrue("foobar" not in registry.records)

    def test_edit_record_with_slash(self):
        # Prepare a new record "foo/bar"
        registry = self.portal.portal_registry
        new_field = TextLine()
        new_record = Record(new_field)
        registry.records["foo/bar"] = new_record

        # the record has no value set
        self.assertIsNone(new_record.value)

        # prepare a request
        request = self.request.clone()
        request.form = {
            "form.widgets.value": "baz",
            "form.buttons.save": "Save",
        }
        request.method = "POST"
        request["TraversalRequestNameStack"] = []

        # get the view and fake the traversal
        edit_form = getMultiAdapter(
            (registry, request),
            name="edit",
        ).publishTraverse(request, "foo/bar")

        # call the view and verify the value has changed
        edit_form()
        self.assertEqual(new_record.value, "baz")
