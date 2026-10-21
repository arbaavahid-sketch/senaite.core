# -*- coding: utf-8 -*-
"""Isolated conversion regression tests; no running Plone site required.

Run directly with Python 2.7 or Python 3. These tests execute the production
view's methods with in-memory transaction/API doubles. They do not replace
ZODB integration tests for simultaneous requests and publisher retries.
"""
import ast
import copy
import logging
import os
import sys
import types
import unittest
from contextlib import contextmanager


class Record(object):
    def __init__(self, **values):
        self.__dict__.update(values)


class ConflictError(Exception):
    pass


@contextmanager
def privileged():
    yield


def load_view(source):
    with open(source, "rb") as stream:
        tree = ast.parse(stream.read(), filename=source)
    # Execute the actual methods, replacing only framework dependencies.
    tree.body = [node for node in tree.body if (
        isinstance(node, ast.ClassDef) and node.name == "ConvertToSampleView"
    ) or (
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "LABELS"
                for t in node.targets)
    )]
    namespace = {
        "BrowserView": object,
        "ViewPageTemplateFile": lambda path: None,
        "IDisableCSRFProtection": None,
        "ConflictError": ConflictError,
        "basestring": str,
        "logger": logging.getLogger("conversion-test"),
    }
    eval(compile(tree, source, "exec"), namespace)
    return namespace


class ConversionTests(unittest.TestCase):
    def setUp(self):
        source = os.environ.get("CONVERSION_SOURCE") or os.path.join(
            os.path.dirname(__file__), "..", "browser",
            "samplerequest", "convert.py")
        self.ns = load_view(source)
        self.context = Record(
            id="TR-26-0048", tracking_code="TR-26-0048",
            created_sample_id="", created_sample_uid="", state="received")
        self.state = {"objects": {}, "counter": 70, "contacts": 0,
                      "catalog": {}, "queue": []}
        self.fail_at = None
        self.calls = 0
        self.rollbacks = 0
        self.view = self.ns["ConvertToSampleView"]()
        self.view.context = self.context
        self.view.request = Record(form={
            "client_uid": "client-8", "sampletype_uid": "type-36",
            "service_uids": ["density"], "sampling_date": "2026-10-20"})
        self.view.labels = self.ns["LABELS"]["en"]
        self.view.error = self.view.created = self.view.created_url = ""
        self.view._resolve_client = lambda form: self.client
        self.view._resolve_contact = self.contact
        self.view._set_creator = lambda obj, userid: None
        self.client = Record(
            objectIds=lambda: list(self.state["objects"]),
            manage_renameObject=self.rename)

        class Client(Record):
            def __getitem__(client, key):
                return self.state["objects"][key]
        self.client = Client(**self.client.__dict__)
        self.ns["api"] = Record(
            security=Record(as_privileged_user=privileged),
            get_id=lambda obj: obj.id,
            get_uid=lambda obj: getattr(obj, "uid", "client-uid"),
            get_parent=lambda obj: self.client,
            get_url=lambda obj: "/clients/client-8/" + obj.id,
            get_review_status=lambda obj: obj.state,
            uncatalog_object=self.uncatalog,
            catalog_object=self.catalog,
            do_transition_for=self.transition)
        self.ns["processQueue"] = self.process_queue
        self.ns["transaction"] = Record(savepoint=self.savepoint)
        self.ns["create_analysisrequest"] = self.create
        self.previous_access = sys.modules.get("AccessControl")
        access = types.ModuleType("AccessControl")
        access.getSecurityManager = lambda: Record(
            getUser=lambda: Record(getId=lambda: "staff"))
        sys.modules["AccessControl"] = access

    def tearDown(self):
        if self.previous_access is None:
            del sys.modules["AccessControl"]
        else:
            sys.modules["AccessControl"] = self.previous_access

    def savepoint(self, **kw):
        state = copy.deepcopy(self.state)
        context = copy.deepcopy(self.context.__dict__)

        def rollback():
            self.rollbacks += 1
            self.state = state
            self.context.__dict__.clear()
            self.context.__dict__.update(context)
        return Record(rollback=rollback)

    def contact(self, client):
        self.state["contacts"] += 1
        return Record(uid="contact-uid")

    def create(self, *args):
        self.created_values = args[2]
        self.calls += 1
        self.state["counter"] += 1
        sample = Record(id="ST36-26-%04d" % self.state["counter"],
                        uid="sample-uid", reindexObject=lambda: None)
        self.state["objects"][sample.id] = sample
        self.catalog(sample, recursive=True)
        if self.fail_at == "create":
            raise ValueError("Partial creation failed")
        return sample

    def paths(self, sample, recursive):
        paths = [sample.id]
        if recursive:
            paths.extend([sample.id + "/density", sample.id + "/distillation"])
        return paths

    def catalog(self, sample, recursive=False):
        for path in self.paths(sample, recursive):
            self.state["queue"].append(("add", path))

    def uncatalog(self, sample, recursive=False):
        for path in self.paths(sample, recursive):
            self.state["queue"].append(("remove", path))

    def process_queue(self):
        while self.state["queue"]:
            action, path = self.state["queue"].pop(0)
            if action == "remove":
                self.state["catalog"].pop(path, None)
            else:
                if path.split("/")[0] not in self.state["objects"]:
                    raise AttributeError(path)
                self.state["catalog"][path] = True
                if path.startswith("TR-") and self.fail_at == "catalog":
                    raise ValueError("Catalog update failed")

    def rename(self, old, new):
        if self.fail_at == "conflict":
            raise ConflictError()
        if self.fail_at == "rename":
            raise ValueError("Rename failed")
        if self.fail_at == "silent_rename":
            return
        sample = self.state["objects"].pop(old)
        sample.id = new
        self.state["objects"][new] = sample

    def transition(self, obj, action):
        if self.fail_at == "transition":
            raise ValueError("Workflow failed")
        obj.state = "in_progress"

    def test_success_preserves_customer_number(self):
        self.view._convert()
        self.assertEqual(self.view.error, "")
        self.assertEqual(self.view.created, "TR-26-0048")
        self.assertEqual(list(self.state["objects"]), ["TR-26-0048"])
        self.assertEqual(self.context.created_sample_uid, "sample-uid")
        self.assertEqual(self.context.state, "in_progress")

    def test_catalog_paths_follow_renamed_sample_and_children(self):
        self.view._convert()
        self.assertEqual(self.view.error, "")
        self.assertEqual(sorted(self.state["catalog"]), [
            "TR-26-0048", "TR-26-0048/density", "TR-26-0048/distillation"])
        self.assertEqual(self.state["queue"], [])

    def test_sampling_date_is_the_actual_collection_date(self):
        self.view._convert()
        self.assertEqual(self.created_values["DateSampled"], "2026-10-20")
        self.assertNotIn("SamplingDate", self.created_values)

    def test_missing_services_do_not_create_sample(self):
        self.view.request.form["service_uids"] = []
        self.view._convert()
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.view.error, self.view.labels["err_services"])

    def test_missing_sample_type_does_not_create_sample(self):
        self.view.request.form["sampletype_uid"] = ""
        self.view._convert()
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.view.error, self.view.labels["err_sampletype"])

    def test_catalog_failure_rolls_back_sample_and_references(self):
        self.assert_atomic_failure("catalog")
        self.assertEqual(self.state["catalog"], {})
        self.assertEqual(self.state["queue"], [])

    def test_repeat_submission_does_not_create_again(self):
        self.view._convert()
        self.view._convert()
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.view.error, self.view.labels["err_existing"])
        self.assertEqual(self.context.created_sample_uid, "sample-uid")

    def test_existing_legacy_id_blocks_even_without_uid(self):
        self.context.created_sample_id = "ST36-26-0071"
        self.view._convert()
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.context.created_sample_id, "ST36-26-0071")

    def test_existing_uid_blocks_even_without_id(self):
        self.context.created_sample_uid = "missing-or-existing-sample"
        self.view._convert()
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.view.error, self.view.labels["err_existing"])

    def test_occupied_number_does_not_create_or_relink(self):
        self.state["objects"]["TR-26-0048"] = Record(id="TR-26-0048")
        self.view._convert()
        self.assertEqual(self.view.error, self.view.labels["err_collision"])
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.state["contacts"], 0)
        self.assertEqual(self.context.created_sample_id, "")
        self.assertEqual(list(self.state["objects"]), ["TR-26-0048"])

    def assert_atomic_failure(self, stage):
        self.fail_at = stage
        self.view._convert()
        self.assertEqual(self.state["objects"], {})
        self.assertEqual(self.state["counter"], 70)
        self.assertEqual(self.state["contacts"], 0)
        self.assertEqual(self.context.created_sample_id, "")
        self.assertEqual(self.context.created_sample_uid, "")
        self.assertEqual(self.context.state, "received")
        self.assertEqual(self.view.created, "")
        self.assertEqual(self.view.created_url, "")
        self.assertEqual(self.view.error, self.view.labels["err_conversion"])

    def test_partial_creation_is_rolled_back(self):
        self.assert_atomic_failure("create")

    def test_failed_rename_is_rolled_back(self):
        self.assert_atomic_failure("rename")

    def test_silent_rename_failure_is_rejected(self):
        self.assert_atomic_failure("silent_rename")

    def test_workflow_failure_is_rolled_back(self):
        self.assert_atomic_failure("transition")

    def test_conflict_reaches_publisher_for_abort_and_retry(self):
        self.fail_at = "conflict"
        with self.assertRaises(ConflictError):
            self.view._convert()
        self.assertEqual(self.view.created, "")
        self.assertEqual(self.view.error, "")

    def test_next_request_is_unaffected_by_previous_collision(self):
        self.state["objects"]["TR-26-0048"] = Record(id="TR-26-0048")
        self.view._convert()
        self.context.id = self.context.tracking_code = "TR-26-0049"
        self.view.error = ""
        self.view._convert()
        self.assertEqual(self.view.created, "TR-26-0049")
        self.assertEqual(self.view.error, "")
        self.assertEqual(len(self.state["objects"]), 2)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
