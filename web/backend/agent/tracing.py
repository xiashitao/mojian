"""Trace writer for agent runs."""
from __future__ import annotations

from typing import Any

from . import hooks, repository


class TraceWriter:
    """Append ordered trace steps for one agent run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._step_index = 0

    def add(
        self,
        step_type: str,
        *,
        input_data: Any = None,
        output_data: Any = None,
        summary: str | None = None,
    ) -> None:
        self._step_index += 1
        repository.add_trace(
            self.run_id,
            self._step_index,
            step_type,
            input_data=input_data,
            output_data=output_data,
            summary=summary,
        )
        # 观测事件:每落一步 trace 广播一次(观察类,hook 失败不影响落库)。
        hooks.dispatch("on_step", {
            "step_type": step_type,
            "step_index": self._step_index,
            "input": input_data,
            "output": output_data,
            "summary": summary,
        }, run_id=self.run_id, match_value=step_type)

