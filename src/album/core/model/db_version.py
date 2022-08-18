from album.core.api.model.db_version import IDBVersion


class DBVersion(IDBVersion):
    #TODO FIX ABSTRACT CLASS BULLSHIT

    def __init__(self, version, major, minor):
        self.version = version
        self.major = major
        self.minor = minor

    def __eq__(self, other):
        return (self.version == other.version) and (self.major == other.major) and (self.minor == other.minor)

    def __lt__(self, other):
        return (self.version < other.version) or (self.version == other.version and self.major < other.major) or (
                    self.version == other.version and self.major == other.major and self.minor < other.minor)

    def __gt__(self, other):
        return (self.version > other.version) or (self.version == other.version and self.major > other.major) or (
                    self.version == other.version and self.major == other.major and self.minor > other.minor)

    def __str__(self):
        return "%s%s%s" % (self.version, self.major, self.minor)

    @classmethod
    def from_string(cls, version_string):
        version = int(version_string.split('.')[0])
        major = int(version_string.split('.')[1])
        minor = int(version_string.split('.')[2])
        return cls(version, major, minor)

