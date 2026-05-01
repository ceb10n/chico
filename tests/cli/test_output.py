"""Tests for chico.cli.output."""

from __future__ import annotations

import pytest

from chico.cli.output import get_console, get_err_console, run_with_progress


class TestGetConsole:
    def test_returns_console(self):
        from rich.console import Console

        assert isinstance(get_console(), Console)

    def test_returns_new_instance_each_call(self):
        assert get_console() is not get_console()


class TestGetErrConsole:
    def test_returns_console(self):
        from rich.console import Console

        assert isinstance(get_err_console(), Console)

    def test_returns_new_instance_each_call(self):
        assert get_err_console() is not get_err_console()


class TestRunWithProgress:
    def test_returns_function_result(self):
        console = get_console()
        result = run_with_progress(console, ["msg"], lambda: 42, interval=0.0)
        assert result == 42

    def test_propagates_exception_from_fn(self):
        console = get_console()
        with pytest.raises(ValueError, match="boom"):
            run_with_progress(
                console,
                ["msg"],
                lambda: (_ for _ in ()).throw(ValueError("boom")),
                interval=0.0,
            )

    def test_cycles_through_messages(self):
        """fn sleeps briefly so the loop runs more than once."""
        import time

        console = get_console()
        calls: list[str] = []
        original_status = console.status

        def tracking_status(msg: str, **kwargs):  # type: ignore[override]
            ctx = original_status(msg, **kwargs)
            original_update = ctx.update

            def tracking_update(new_msg: str) -> None:
                calls.append(new_msg)
                original_update(new_msg)

            ctx.update = tracking_update  # type: ignore[method-assign]
            return ctx

        console.status = tracking_status  # type: ignore[method-assign]

        def slow_fn() -> int:
            time.sleep(0.05)
            return 1

        run_with_progress(console, ["a", "b", "c"], slow_fn, interval=0.01)
        assert len(calls) >= 1

    def test_works_with_single_message(self):
        console = get_console()
        result = run_with_progress(console, ["only one"], lambda: "done", interval=0.0)
        assert result == "done"
