from __future__ import annotations

import unittest
from unittest.mock import patch

from websearch_agents.rich_output import (
    RICH_INSTALL_MESSAGE,
    print_json_rich,
    rich_available,
    should_use_rich,
)


class RichOutputTests(unittest.TestCase):
    def test_rich_available_returns_false_when_imports_fail(self) -> None:
        with patch("importlib.import_module", side_effect=ImportError):
            self.assertFalse(rich_available())

    def test_print_json_rich_raises_clear_error_without_dependency(self) -> None:
        with patch("importlib.import_module", side_effect=ImportError):
            with self.assertRaisesRegex(RuntimeError, "Rich output requested"):
                print_json_rich({"ok": True})

        self.assertIn("pip install -e .[ui]", RICH_INSTALL_MESSAGE)

    def test_should_use_rich_auto_enables_for_tty_text(self) -> None:
        self.assertTrue(
            should_use_rich(
                explicit_rich=False,
                plain=False,
                stdout_is_tty=True,
                rich_installed=True,
                json_mode=False,
            )
        )
        self.assertFalse(
            should_use_rich(
                explicit_rich=False,
                plain=False,
                stdout_is_tty=True,
                rich_installed=True,
                json_mode=True,
            )
        )
        self.assertFalse(
            should_use_rich(
                explicit_rich=False,
                plain=True,
                stdout_is_tty=True,
                rich_installed=True,
                json_mode=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
