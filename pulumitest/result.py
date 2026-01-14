import unittest
from pulumi import automation as auto
from pulumi.automation.events import OpType
from pulumitest.change_summary import ChangeSummary
from typing import Optional


class Result:
    test_case: unittest.TestCase
    
    def __init__(self, test_case: unittest.TestCase):
        self.test_case = test_case


class PreviewResult(Result):
    preview_result: auto.PreviewResult

    def __init__(self, test_case: unittest.TestCase, preview_result: auto.PreviewResult):
        super().__init__(test_case)
        self.preview_result = preview_result

    @property
    def change_summary(self) -> dict:
        """Direct access to operation counts (OpType -> count mapping)."""
        return self.preview_result.change_summary

    def has_no_deletes(self):
        change_summary = ChangeSummary(self.preview_result.change_summary)
        unexpected_ops = change_summary.where_op_not_equals(OpType.DELETE, OpType.DELETE_REPLACED, OpType.REPLACE)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no deletes, got {unexpected_ops}\n{self.preview_result.stdout}")
    
    def has_no_changes(self):
        change_summary = ChangeSummary(self.preview_result.change_summary)
        unexpected_ops = change_summary.where_op_not_equals(OpType.SAME)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no changes, got {unexpected_ops}\n{self.preview_result.stdout}")
    
    def has_no_replacements(self):
        change_summary = ChangeSummary(self.preview_result.change_summary)
        unexpected_ops = change_summary.where_op_not_equals(OpType.REPLACE, OpType.CREATE_REPLACEMENT, OpType.DELETE_REPLACED, OpType.DISCARD_REPLACED, OpType.IMPORT_REPLACEMENT, OpType.READ_REPLACEMENT)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no replacements, got {unexpected_ops}\n{self.preview_result.stdout}")


class RefreshResult(Result):
    refresh_result: auto.UpResult

    def __init__(self, test_case: unittest.TestCase, refresh_result: auto.UpResult):
        super().__init__(test_case)
        self.refresh_result = refresh_result

    @property
    def change_summary(self) -> dict:
        """Direct access to resource changes (OpType -> count mapping)."""
        return self.refresh_result.summary.resource_changes

    @property
    def summary(self):
        """Direct access to refresh summary."""
        return self.refresh_result.summary

    def has_no_changes(self):
        change_summary = ChangeSummary(self.refresh_result.summary.resource_changes)
        unexpected_ops = change_summary.where_op_not_equals(OpType.SAME)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no changes, got {unexpected_ops}\n{self.refresh_result.stdout}")


class UpdateResult(Result):
    update_result: auto.UpResult

    def __init__(self, test_case: unittest.TestCase, update_result: auto.UpResult):
        super().__init__(test_case)
        self.update_result = update_result

    @property
    def outputs(self) -> dict:
        """Direct access to stack outputs."""
        return self.update_result.outputs

    @property
    def summary(self):
        """Direct access to deployment summary."""
        return self.update_result.summary

    @property
    def change_summary(self) -> dict:
        """Direct access to resource changes (OpType -> count mapping)."""
        return self.update_result.summary.resource_changes

    def has_no_deletes(self):
        change_summary = ChangeSummary(self.update_result.summary.resource_changes)
        unexpected_ops = change_summary.where_op_not_equals(OpType.DELETE, OpType.DELETE_REPLACED, OpType.REPLACE)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no deletes, got {unexpected_ops}\n{self.update_result.stdout}")
    
    def has_no_changes(self):
        change_summary = ChangeSummary(self.update_result.summary.resource_changes)
        unexpected_ops = change_summary.where_op_not_equals(OpType.SAME)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no changes, got {unexpected_ops}\n{self.update_result.stdout}")
    
    def has_no_replacements(self):
        change_summary = ChangeSummary(self.update_result.summary.resource_changes)
        unexpected_ops = change_summary.where_op_not_equals(OpType.REPLACE, OpType.CREATE_REPLACEMENT, OpType.DELETE_REPLACED, OpType.DISCARD_REPLACED, OpType.IMPORT_REPLACEMENT, OpType.READ_REPLACEMENT)
        if len(unexpected_ops) > 0:
            self.test_case.fail(f"expected no replacements, got {unexpected_ops}\n{self.update_result.stdout}")