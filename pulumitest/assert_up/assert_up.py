import unittest
from pulumi import automation as auto
from pulumi.automation.events import OpType
from pulumitest.change_summary import ChangeSummary

def has_no_deletes(t: unittest.TestCase, up: auto.UpResult):
    change_summary = ChangeSummary(up.summary.resource_changes)
    unexpected_ops = change_summary.where_op_not_equals(OpType.DELETE, OpType.DELETE_REPLACED, OpType.REPLACE)
    if len(unexpected_ops) > 0:
        t.fail(f"expected no deletes, got {unexpected_ops}\n{up.stdout}")

def has_no_changes(t: unittest.TestCase, up: auto.UpResult):
    change_summary = ChangeSummary(up.summary.resource_changes)
    unexpected_ops = change_summary.where_op_not_equals(OpType.SAME)
    if len(unexpected_ops) > 0:
        t.fail(f"expected no changes, got {unexpected_ops}\n{up.stdout}")

def has_no_replacements(t: unittest.TestCase, up: auto.UpResult):
    change_summary = ChangeSummary(up.summary.resource_changes)
    unexpected_ops = change_summary.where_op_not_equals(OpType.REPLACE, OpType.CREATE_REPLACEMENT, OpType.DELETE_REPLACED, OpType.DISCARD_REPLACED, OpType.IMPORT_REPLACEMENT, OpType.READ_REPLACEMENT)
    if len(unexpected_ops) > 0:
        t.fail(f"expected no replacements, got {unexpected_ops}\n{up.stdout}")
