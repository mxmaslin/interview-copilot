from __future__ import annotations

import copilot.screenshot_solve as ss


def test_screenshot_system_no_theory_section_instruction() -> None:
    assert "Без секции «Теория»" in ss.SCREENSHOT_SYSTEM
    assert "Если теория —" not in ss.SCREENSHOT_SYSTEM


def test_screenshot_user_text_forbids_theory() -> None:
    assert "Теория" in ss.USER_TEXT
    assert "Не добавляй" in ss.USER_TEXT
