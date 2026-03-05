"""Test result assertion methods using mock Pulumi results."""

import pytest
from unittest.mock import MagicMock
from pulumi.automation.events import OpType
from pulumitest.results import PreviewResult, UpdateResult, RefreshResult, _ChangeSummary


def test_change_summary_where_op_not_equals():
    cs = _ChangeSummary({OpType.SAME: 3, OpType.CREATE: 1})
    result = cs.where_op_not_equals(OpType.SAME)
    assert result == {OpType.CREATE: 1}


def test_change_summary_all_same():
    cs = _ChangeSummary({OpType.SAME: 5})
    result = cs.where_op_not_equals(OpType.SAME)
    assert result == {}


def test_preview_has_no_changes_passes():
    mock_result = MagicMock()
    mock_result.change_summary = {OpType.SAME: 3}
    mock_result.stdout = ""
    result = PreviewResult(mock_result)
    result.has_no_changes()  # Should not raise


def test_preview_has_no_changes_fails():
    mock_result = MagicMock()
    mock_result.change_summary = {OpType.SAME: 3, OpType.CREATE: 1}
    mock_result.stdout = "output"
    result = PreviewResult(mock_result)
    with pytest.raises(AssertionError, match="expected no changes"):
        result.has_no_changes()


def test_preview_has_no_deletes_passes():
    """has_no_deletes passes when no delete-type ops exist."""
    mock_result = MagicMock()
    mock_result.change_summary = {OpType.SAME: 3, OpType.CREATE: 1}
    mock_result.stdout = ""
    result = PreviewResult(mock_result)
    result.has_no_deletes()  # Should not raise - no deletes present


def test_preview_has_no_deletes_fails():
    """has_no_deletes fails when delete-type ops are present."""
    mock_result = MagicMock()
    mock_result.change_summary = {OpType.SAME: 3, OpType.DELETE: 1}
    mock_result.stdout = "output"
    result = PreviewResult(mock_result)
    with pytest.raises(AssertionError, match="expected no deletes"):
        result.has_no_deletes()


def test_update_has_no_changes_none_resource_changes():
    """UpdateResult.has_no_changes passes when resource_changes is None."""
    mock_result = MagicMock()
    mock_result.summary.resource_changes = None
    result = UpdateResult(mock_result)
    result.has_no_changes()  # Should not raise


def test_update_has_no_changes_passes():
    mock_result = MagicMock()
    mock_result.summary.resource_changes = {OpType.SAME: 5}
    result = UpdateResult(mock_result)
    result.has_no_changes()


def test_update_has_no_changes_fails():
    mock_result = MagicMock()
    mock_result.summary.resource_changes = {OpType.SAME: 3, OpType.UPDATE: 1}
    mock_result.stdout = "output"
    result = UpdateResult(mock_result)
    with pytest.raises(AssertionError, match="expected no changes"):
        result.has_no_changes()


def test_refresh_has_no_changes_none():
    mock_result = MagicMock()
    mock_result.summary.resource_changes = None
    result = RefreshResult(mock_result)
    result.has_no_changes()  # Should not raise


def test_refresh_has_no_changes_passes():
    mock_result = MagicMock()
    mock_result.summary.resource_changes = {OpType.SAME: 2}
    result = RefreshResult(mock_result)
    result.has_no_changes()


def test_refresh_has_no_changes_fails():
    mock_result = MagicMock()
    mock_result.summary.resource_changes = {OpType.SAME: 2, OpType.UPDATE: 1}
    mock_result.stdout = "output"
    result = RefreshResult(mock_result)
    with pytest.raises(AssertionError, match="expected no changes"):
        result.has_no_changes()


def test_update_outputs():
    mock_result = MagicMock()
    mock_result.outputs = {"key": "value"}
    result = UpdateResult(mock_result)
    assert result.outputs == {"key": "value"}


def test_update_summary():
    mock_result = MagicMock()
    mock_result.summary = "mock_summary"
    result = UpdateResult(mock_result)
    assert result.summary == "mock_summary"
