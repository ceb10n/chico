"""Tests for chico.core.provider."""

from __future__ import annotations

from chico.core.provider import Provider
from chico.core.resource import ChangeType, Diff, Resource, Result, ResultStatus


class TestProviderProtocol:
    def test_valid_implementation_is_instance(self):
        class MyResource:
            @property
            def resource_id(self) -> str:
                return "r1"

            def desired_state(self) -> dict:
                return {}

            def current_state(self) -> dict:
                return {}

            def diff(self) -> Diff:
                return Diff(change_type=ChangeType.NONE, resource_id=self.resource_id)

            def apply(self) -> Result:
                return Result(status=ResultStatus.OK, resource_id=self.resource_id)

        class MyProvider:
            @property
            def name(self) -> str:
                return "my-provider"

            def list_resources(self) -> list[Resource]:
                return [MyResource()]

        assert isinstance(MyProvider(), Provider)

    def test_missing_name_is_not_instance(self):
        class NoName:
            def list_resources(self) -> list:
                return []

        assert not isinstance(NoName(), Provider)

    def test_missing_list_resources_is_not_instance(self):
        class NoList:
            @property
            def name(self) -> str:
                return "x"

        assert not isinstance(NoList(), Provider)

    def test_list_resources_returns_resources(self):
        class MyResource:
            @property
            def resource_id(self) -> str:
                return "r1"

            def desired_state(self) -> dict:
                return {}

            def current_state(self) -> dict:
                return {}

            def diff(self) -> Diff:
                return Diff(change_type=ChangeType.NONE, resource_id=self.resource_id)

            def apply(self) -> Result:
                return Result(status=ResultStatus.OK, resource_id=self.resource_id)

        class MyProvider:
            @property
            def name(self) -> str:
                return "my-provider"

            def list_resources(self) -> list[Resource]:
                return [MyResource(), MyResource()]

        provider = MyProvider()
        resources = provider.list_resources()
        assert len(resources) == 2
        assert all(isinstance(r, Resource) for r in resources)

    def test_empty_provider_returns_no_resources(self):
        class EmptyProvider:
            @property
            def name(self) -> str:
                return "empty"

            def list_resources(self) -> list[Resource]:
                return []

        assert EmptyProvider().list_resources() == []
