class GroupNameVersion:

    def __init__(self, group: str, name: str, version: str) -> None:
        self.group = group
        self.name = name
        self.version = version

    def __str__(self) -> str:
        return f"{self.group}:{self.name}:{self.version}"

    def __eq__(self, o: object) -> bool:
        return isinstance(
            o, GroupNameVersion
        ) and o.group == self.group and o.name == self.name and o.version == self.version
