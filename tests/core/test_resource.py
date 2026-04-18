"""Tests for chico.core.resource."""

from __future__ import annotations

from chico.core.resource import (
    ChangeType,
    Diff,
    FieldChange,
    Resource,
    Result,
    ResultStatus,
)


class TestChangeType:
    def test_values(self):
        assert ChangeType.ADD == "add"
        assert ChangeType.MODIFY == "modify"
        assert ChangeType.REMOVE == "remove"
        assert ChangeType.NONE == "none"

    def test_is_str(self):
        assert isinstance(ChangeType.ADD, str)


class TestFieldChange:
    def test_stores_from_and_to(self):
        fc = FieldChange(from_value=1, to_value=2)
        assert fc.from_value == 1
        assert fc.to_value == 2

    def test_accepts_none_values(self):
        fc = FieldChange(from_value=None, to_value="hello")
        assert fc.from_value is None
        assert fc.to_value == "hello"

    def test_accepts_any_type(self):
        fc = FieldChange(from_value={"a": 1}, to_value=[1, 2, 3])
        assert fc.from_value == {"a": 1}
        assert fc.to_value == [1, 2, 3]


class TestDiff:
    def test_has_changes_true_for_add(self):
        diff = Diff(change_type=ChangeType.ADD, resource_id="res-1")
        assert diff.has_changes is True

    def test_has_changes_true_for_modify(self):
        diff = Diff(change_type=ChangeType.MODIFY, resource_id="res-1")
        assert diff.has_changes is True

    def test_has_changes_true_for_remove(self):
        diff = Diff(change_type=ChangeType.REMOVE, resource_id="res-1")
        assert diff.has_changes is True

    def test_has_changes_false_for_none(self):
        diff = Diff(change_type=ChangeType.NONE, resource_id="res-1")
        assert diff.has_changes is False

    def test_changes_defaults_to_empty_dict(self):
        diff = Diff(change_type=ChangeType.NONE, resource_id="res-1")
        assert diff.changes == {}

    def test_changes_are_independent_between_instances(self):
        d1 = Diff(change_type=ChangeType.MODIFY, resource_id="r1")
        d2 = Diff(change_type=ChangeType.MODIFY, resource_id="r2")
        d1.changes["field"] = FieldChange(from_value=0, to_value=1)
        assert "field" not in d2.changes

    def test_stores_field_changes(self):
        fc = FieldChange(from_value=False, to_value=True)
        diff = Diff(
            change_type=ChangeType.MODIFY,
            resource_id="res-1",
            changes={"enabled": fc},
        )
        assert diff.changes["enabled"] is fc


class TestResultStatus:
    def test_values(self):
        assert ResultStatus.OK == "ok"
        assert ResultStatus.ERROR == "error"
        assert ResultStatus.SKIPPED == "skipped"

    def test_is_str(self):
        assert isinstance(ResultStatus.OK, str)


class TestResult:
    def test_ok_property_true_when_status_ok(self):
        result = Result(status=ResultStatus.OK, resource_id="res-1")
        assert result.ok is True

    def test_ok_property_false_when_status_error(self):
        result = Result(status=ResultStatus.ERROR, resource_id="res-1")
        assert result.ok is False

    def test_ok_property_false_when_status_skipped(self):
        result = Result(status=ResultStatus.SKIPPED, resource_id="res-1")
        assert result.ok is False

    def test_message_defaults_to_empty_string(self):
        result = Result(status=ResultStatus.OK, resource_id="res-1")
        assert result.message == ""

    def test_stores_custom_message(self):
        result = Result(status=ResultStatus.ERROR, resource_id="res-1", message="boom")
        assert result.message == "boom"


class TestResourceProtocol:
    def test_valid_implementation_is_instance(self):
        class MyResource:
            @property
            def resource_id(self) -> str:
                return "my-resource"

            def desired_state(self) -> dict:
                return {}

            def current_state(self) -> dict:
                return {}

            def diff(self) -> Diff:
                return Diff(change_type=ChangeType.NONE, resource_id=self.resource_id)

            def apply(self) -> Result:
                return Result(status=ResultStatus.OK, resource_id=self.resource_id)

        assert isinstance(MyResource(), Resource)

    def test_missing_method_is_not_instance(self):
        class Incomplete:
            @property
            def resource_id(self) -> str:
                return "x"

            def desired_state(self) -> dict:
                return {}

            # current_state, diff, apply missing

        assert not isinstance(Incomplete(), Resource)
