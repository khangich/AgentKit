"""Minimal UI description DSL for AgentKit apps."""

from __future__ import annotations

import contextlib
import contextvars
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Component:
    type: str
    id: str
    props: Dict[str, Any]


@dataclass
class PageSpec:
    title: str
    description: Optional[str] = None
    components: List[Component] = field(default_factory=list)

    def add(self, component: Component) -> None:
        self.components.append(component)


class RuntimeContext:
    """Holds runtime values for executing the AgentKit DSL."""

    def __init__(
        self,
        mode: str = "render",
        inputs: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        trigger: Optional[str] = None,
    ) -> None:
        self.mode = mode
        self.inputs = inputs or {}
        self.files = files or {}
        self.trigger = trigger
        self.current_page: Optional[PageSpec] = None
        self.rendered_page: Optional[PageSpec] = None
        self._slug_counts: Dict[str, int] = {}
        self.run_ids: List[str] = []

    # Component helpers -------------------------------------------------

    def _slugify(self, label: str, prefix: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        if not base:
            base = prefix
        key = f"{prefix}-{base}"
        count = self._slug_counts.get(key, 0) + 1
        self._slug_counts[key] = count
        if count > 1:
            return f"{base}-{count}"
        return base

    def register(self, type_: str, label: str, props: Optional[Dict[str, Any]] = None) -> str:
        if not self.current_page:
            raise RuntimeError("ui.page() must be active before adding components")
        component_id = props.get("id") if props and "id" in props else self._slugify(label, type_)
        component = Component(type=type_, id=component_id, props={"label": label, **(props or {})})
        self.current_page.add(component)
        return component_id

    def resolve_value(self, component_id: str, kind: str) -> Any:
        if kind == "file":
            return self.files.get(component_id, [])
        if kind == "button":
            return self.trigger == component_id
        return self.inputs.get(component_id)

    def set_page(self, page: PageSpec) -> None:
        self.current_page = page
        self.rendered_page = page

    def record_run(self, run_id: str) -> None:
        self.run_ids.append(run_id)


_runtime_var: contextvars.ContextVar[Optional[RuntimeContext]] = contextvars.ContextVar(
    "agentkit_runtime", default=None
)


@contextlib.contextmanager
def page(title: str, description: str | None = None):
    runtime = ensure_runtime()
    previous_page = runtime.current_page
    spec = PageSpec(title=title, description=description)
    runtime.set_page(spec)
    try:
        yield spec
    finally:
        runtime.current_page = previous_page


class ValueRef:
    def __init__(self, component_id: str, kind: str, default: Any = None):
        self.component_id = component_id
        self.kind = kind
        self.default = default

    @property
    def value(self) -> Any:
        runtime = get_runtime()
        if not runtime:
            return self.default
        value = runtime.resolve_value(self.component_id, self.kind)
        return value if value is not None else self.default

    def __str__(self) -> str:
        value = self.value
        return "" if value is None else str(value)

    def __bool__(self) -> bool:  # pragma: no cover - simple proxy
        value = self.value
        if isinstance(value, list):
            return bool(value)
        return bool(value)


def text_input(label: str, placeholder: str = "") -> ValueRef:
    runtime = ensure_runtime()
    component_id = runtime.register("text", label, {"placeholder": placeholder})
    return ValueRef(component_id, kind="text", default="")


def file_uploader(
    label: str,
    accept: Optional[List[str]] = None,
    multiple: bool = True,
) -> ValueRef:
    runtime = ensure_runtime()
    props = {"accept": accept or [], "multiple": multiple}
    component_id = runtime.register("file", label, props)
    return ValueRef(component_id, kind="file", default=[])


def button(label: str) -> bool:
    runtime = ensure_runtime()
    component_id = runtime.register("button", label)
    return bool(runtime.resolve_value(component_id, "button"))


def chat() -> None:
    runtime = ensure_runtime()
    runtime.register("chat", "Conversation", {})


def get_runtime() -> Optional[RuntimeContext]:
    return _runtime_var.get()


def ensure_runtime() -> RuntimeContext:
    runtime = _runtime_var.get()
    if runtime is None:
        runtime = RuntimeContext()
        _runtime_var.set(runtime)
    return runtime


@contextlib.contextmanager
def use_runtime(runtime: RuntimeContext):
    token = _runtime_var.set(runtime)
    try:
        yield runtime
    finally:
        _runtime_var.reset(token)


__all__ = [
    "RuntimeContext",
    "page",
    "text_input",
    "file_uploader",
    "button",
    "chat",
    "use_runtime",
    "get_runtime",
]
