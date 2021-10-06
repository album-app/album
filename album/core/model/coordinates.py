import re


class Coordinates:
    """Class for the Coordinates of a solution."""

    def __init__(self, group: str, name: str, version: str) -> None:
        self.group = group
        self.name = name
        self.version = version
        self.group_path = self._to_path(group)
        self.name_path = self._to_path(name)
        self.version_path = self._to_path(version)

    def __str__(self) -> str:
        return f"{self.group}:{self.name}:{self.version}"

    def __eq__(self, o: object) -> bool:
        return isinstance(
            o, Coordinates
        ) and o.group == self.group and o.name == self.name and o.version == self.version

    @staticmethod
    def _to_path(str_input: str):
        """Replaces all invalid characters with '_', replaces capital letters with their small version.

        Args:
            str_input:
                The string to prepare.

        Returns:
            The replaced version of the string.

        """
        str_input = str_input.casefold().encode("ascii", "ignore").decode()
        return re.sub('\W', '_', str_input)
