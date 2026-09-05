from backend.models.job import Job


class Planner:

    def plan(self, user_request: str) -> list[Job]:
        """
        Converts a user request into planned jobs.

        Actual LLM-based planning will be added later.
        """

        print(f"Planning request: {user_request}")

        # Temporary placeholder
        return []