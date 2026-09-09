from typing import Any

from jsonschema import ValidationError
from jsonschema import validate


class ToolValidator:

    def validate(
        self,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> tuple[bool, str | None]:

        try:
            validate(
                instance=arguments,
                schema=schema,
            )

            return True, None

        except ValidationError as exc:
            return False, exc.message