import unittest
from pulumi import automation as auto
from pulumi.automation.events import OpType
from pulumitest.change_summary import ChangeSummary

def has_no_changes(t: unittest.TestCase, refresh: auto.UpResult) -> None:
    resource_changes = refresh.summary.resource_changes
    if resource_changes is None:
        return
    change_summary = ChangeSummary(resource_changes)
    unexpected_ops = change_summary.where_op_not_equals(OpType.SAME)
    if len(unexpected_ops) > 0:
        t.fail(f"expected no changes, got {unexpected_ops}\n{refresh.stdout}")