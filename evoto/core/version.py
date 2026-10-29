"""
Semantic versioning helpers.

Single source for SDK version plus compare / constraint checks.
"""

import re

# SDK version - single source of truth
SDK_VERSION = "3.0.1"

# Minimum host API version required by this SDK
MIN_API_VERSION = "1.0.0"

# Maximum host API version this SDK targets
MAX_API_VERSION = "1.99.99"

# major.minor.patch (patch optional)
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


class Version:
    """
    Semantic version MAJOR.MINOR.PATCH.

    - MAJOR: breaking changes
    - MINOR: backwards-compatible features
    - PATCH: bug fixes, compatible
    """

    __slots__ = ("major", "minor", "patch")

    def __init__(self, version_str: str):
        """
        Parse a version string.

        Args:
            version_str: e.g. "1.0.0", "1.2", "2.0"

        Raises:
            ValueError: invalid format
        """
        self.major, self.minor, self.patch = self._parse(version_str)

    @staticmethod
    def _parse(version_str: str) -> tuple[int, int, int]:
        """Parse into (major, minor, patch)."""
        if not version_str or not isinstance(version_str, str):
            raise ValueError(f"Invalid version string: {version_str!r}")
        s = version_str.strip()
        m = _VERSION_RE.match(s)
        if not m:
            raise ValueError(f"Invalid version format: {version_str!r}")
        major = int(m.group(1))
        minor = int(m.group(2))
        patch = int(m.group(3)) if m.group(3) is not None else 0
        return (major, minor, patch)

    def __repr__(self) -> str:
        return f"Version({self.major}.{self.minor}.{self.patch})"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    def is_compatible_with(self, other: "Version") -> bool:
        """
        Same major version counts as compatible; self must be >= other.

        Used to validate host API version against SDK minimum.
        """
        if not isinstance(other, Version):
            return False
        if self.major != other.major:
            return False
        return self >= other

    @staticmethod
    def satisfies(version: str, constraint: str) -> bool:
        """
        Check whether version satisfies a constraint expression.

        Supported forms:
        - ">=1.0.0"
        - "<=2.0.0"
        - ">1.0.0"
        - "<2.0.0"
        - "==1.0.0"
        - ">=1.0.0,<2.0.0"  (comma-separated AND)

        Args:
            version: version to test
            constraint: constraint expression

        Returns:
            True if all clauses pass
        """
        try:
            v = Version(version)
        except ValueError:
            return False

        constraints = [c.strip() for c in constraint.split(",") if c.strip()]

        for c in constraints:
            c = c.strip()
            if c.startswith(">="):
                other = Version(c[2:].strip())
                if not (v >= other):
                    return False
            elif c.startswith("<="):
                other = Version(c[2:].strip())
                if not (v <= other):
                    return False
            elif c.startswith(">"):
                other = Version(c[1:].strip())
                if not (v > other):
                    return False
            elif c.startswith("<"):
                other = Version(c[1:].strip())
                if not (v < other):
                    return False
            elif c.startswith("=="):
                other = Version(c[2:].strip())
                if v != other:
                    return False
            else:
                # bare version means >=
                other = Version(c)
                if not (v >= other):
                    return False
        return True
