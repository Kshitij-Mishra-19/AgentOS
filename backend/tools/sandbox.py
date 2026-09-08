from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxPolicy:
    allow_execution: bool = True
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_process_creation: bool = False


class SandboxManager:

    def __init__(self):
        self._policies: dict[str, SandboxPolicy] = {}

    def set_policy(
        self,
        tool_name: str,
        policy: SandboxPolicy,
    ) -> None:

        self._policies[tool_name] = policy

    def get_policy(
        self,
        tool_name: str,
    ) -> SandboxPolicy:

        return self._policies.get(
            tool_name,
            SandboxPolicy(),
        )

    def validate(
        self,
        tool_name: str,
    ) -> bool:

        policy = self.get_policy(tool_name)

        return policy.allow_execution