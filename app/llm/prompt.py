from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ValidationError

_JINJA_ENV = Environment(
    autoescape=False,  # noqa: S701
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class Prompt(BaseModel):
    name: str
    template: str
    config: dict[str, Any] | None = None
    model: str
    tools: list[str]

    def format(self, arguments: dict[str, Any] | None = None) -> str:
        context = dict(arguments or {})
        context.setdefault("tools", self.tools)
        context.setdefault("model", self.model)
        template = _JINJA_ENV.from_string(self.template)
        return template.render(**context)


class PromptRegistry:
    """Loads YAML prompt definitions from disk and exposes them by name."""

    DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "prompts"

    def __init__(self, prompt_dir: Path | None = None) -> None:
        self._prompt_dir = prompt_dir if prompt_dir else self.DEFAULT_PATH
        self._prompts: dict[str, Prompt] = {}
        self._load_prompts()

    def get_prompt(self, name: str) -> Prompt:
        try:
            return self._prompts[name]
        except KeyError as exc:
            raise KeyError(f"Prompt '{name}' is not registered.") from exc

    def _load_prompts(self) -> None:
        for pattern in ("*.yml", "*.yaml"):
            for file_path in sorted(self._prompt_dir.glob(pattern)):
                self._register_prompt(file_path)

    def _register_prompt(self, file_path: Path) -> None:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)

        if "name" not in payload:
            raise ValueError(f"Prompt configuration in file {file_path} is missing name.")
        name = payload["name"]

        try:
            self._prompts[name] = Prompt.model_validate(payload)
        except ValidationError as excp:
            raise ValueError(f"Invalid prompt configuration in file {file_path}.") from excp
