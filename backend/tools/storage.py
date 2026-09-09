import json
from pathlib import Path
from typing import Any


class JSONStorage:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return {}

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError(
                    "Storage file must contain a JSON object."
                )

            return data

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON storage file: {exc}"
            ) from exc

    def save(self, data: dict[str, Any]) -> None:
        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.file_path.with_suffix(
            self.file_path.suffix + ".tmp"
        )

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
            )

        temp_path.replace(self.file_path)