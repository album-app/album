"""Validate that test resource solutions use the correct album_api_version.

All test resource solution files must use EXPECTED_API_VERSION (which matches
DefaultValues.runner_api_package_version) unless they are deliberately pinned to
an older version. Deliberately-old files must contain a comment on the
album_api_version line explaining why.

This prevents silent drift between the framework default and test resources.
"""

import re
import unittest
from pathlib import Path

from album.core.model.default_values import DefaultValues

# The expected API version — derived from the framework default.
# This must match TEST_ALBUM_API_VERSION in test_common.py.
EXPECTED_API_VERSION = DefaultValues.runner_api_package_version.value

# Resource files that are deliberately pinned to an old API version.
# Each must have a comment on the album_api_version line explaining why.
DELIBERATELY_OLD_SOLUTIONS = {
    "solution17_schema0.py",  # tests old solution schema (0.4.1)
    "solution19_outdated_parent.py",  # deliberately outdated (0.5.5)
    "solution21_backwards_compatibility.py",  # backwards compat test (0.0.0)
    "solution21_backwards_compatibility_parent.py",  # backwards compat test (0.0.0)
    "solution21_backwards_compatibility_with_parent.py",  # backwards compat test (0.0.0)
    "solution_broken_lock.py",  # broken lock scenario (0.4.1)
    "_build_resource_files.py",  # catalog index test data (0.1.1)
}

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"

# Matches album_api_version="..." or "album_api_version": "..."
API_VERSION_PATTERN = re.compile(r"""album_api_version\s*[=:]\s*["']([^"']+)["']""")


class TestIntegrationResourceApiVersion(unittest.TestCase):
    """Ensure test resource solutions stay in sync with the framework default."""

    @staticmethod
    def _is_inside_triple_quoted_string(content: str, pos: int) -> bool:
        """Check whether *pos* falls inside a triple-quoted string."""
        in_triple = False
        quote_char = None
        i = 0
        while i < len(content):
            if i >= pos:
                return in_triple
            for q in ('"""', "'''"):
                if content[i : i + 3] == q:
                    if not in_triple:
                        in_triple = True
                        quote_char = q
                        i += 3
                        break
                    elif q == quote_char:
                        in_triple = False
                        quote_char = None
                        i += 3
                        break
            else:
                i += 1
        return in_triple

    def test_resource_solutions_use_current_api_version(self):
        """Every non-deliberately-old resource solution must use EXPECTED_API_VERSION."""
        mismatched = []

        for py_file in sorted(RESOURCES_DIR.rglob("*.py")):
            if py_file.name in DELIBERATELY_OLD_SOLUTIONS:
                continue

            content = py_file.read_text()
            for match in API_VERSION_PATTERN.finditer(content):
                found_version = match.group(1)
                if found_version != EXPECTED_API_VERSION:
                    line_num = content[: match.start()].count("\n") + 1
                    line = content.splitlines()[line_num - 1]
                    # Skip if has a deliberate comment
                    if (
                        "deliberately" in line.lower()
                        or "do not change" in line.lower()
                    ):
                        continue
                    # Skip if inside a triple-quoted string (e.g. solution15's
                    # inner get_solution_content() which embeds an old child solution)
                    if self._is_inside_triple_quoted_string(content, match.start()):
                        continue
                    mismatched.append(
                        f"{py_file.relative_to(RESOURCES_DIR)}:{line_num} "
                        f'has album_api_version="{found_version}" '
                        f'(expected "{EXPECTED_API_VERSION}")'
                    )

        if mismatched:
            self.fail(
                f"The following resource files have an album_api_version that does not "
                f'match EXPECTED_API_VERSION ("{EXPECTED_API_VERSION}"):\n'
                + "\n".join(f"  - {m}" for m in mismatched)
                + "\n\nUpdate them or add to DELIBERATELY_OLD_SOLUTIONS with a comment."
            )

    def test_deliberately_old_solutions_have_comments(self):
        """Every deliberately-old solution must have a comment explaining why."""
        missing_comments = []

        for filename in sorted(DELIBERATELY_OLD_SOLUTIONS):
            py_file = RESOURCES_DIR / filename
            if not py_file.exists():
                continue

            content = py_file.read_text()
            for match in API_VERSION_PATTERN.finditer(content):
                found_version = match.group(1)
                if found_version == EXPECTED_API_VERSION:
                    continue  # not actually old
                line_num = content[: match.start()].count("\n") + 1
                line = content.splitlines()[line_num - 1]
                if "#" not in line:
                    missing_comments.append(
                        f'{filename}:{line_num} uses "{found_version}" '
                        f"but has no comment explaining why"
                    )

        if missing_comments:
            self.fail(
                "Deliberately-old solutions must have a comment on the "
                "album_api_version line:\n"
                + "\n".join(f"  - {m}" for m in missing_comments)
            )

    def test_environment_yml_uses_current_api_version(self):
        """Environment YAML files in test resources must reference the current API version."""
        env_yml_pattern = re.compile(
            r"album-solution-api[=<>~!]+([0-9][0-9a-zA-Z._-]*)"
        )
        mismatched = []

        for yml_file in sorted(RESOURCES_DIR.rglob("*.yml")):
            if "conda-lock" in yml_file.name:
                continue  # lock files are auto-generated
            content = yml_file.read_text()
            for match in env_yml_pattern.finditer(content):
                found_version = match.group(1)
                if found_version != EXPECTED_API_VERSION:
                    line_num = content[: match.start()].count("\n") + 1
                    mismatched.append(
                        f"{yml_file.relative_to(RESOURCES_DIR)}:{line_num} "
                        f"has album-solution-api={found_version} "
                        f"(expected {EXPECTED_API_VERSION})"
                    )

        if mismatched:
            self.fail(
                f"The following YAML files reference an outdated album-solution-api version:\n"
                + "\n".join(f"  - {m}" for m in mismatched)
            )


if __name__ == "__main__":
    unittest.main()
