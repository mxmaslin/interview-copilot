#!/usr/bin/env python3
"""Импорт резюме в context/resume.md (stdin, файл или hh.ru API с токеном)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESUME_MD = ROOT / "context" / "resume.md"
URL_FILE = ROOT / "context" / "resume.hh-url"
DEFAULT_RESUME_ID = "YOUR_HH_RESUME_ID"
HH_API = "https://api.hh.ru/resumes/{resume_id}"
HH_MINE_API = "https://api.hh.ru/resumes/mine"
EXA_CONTENTS_API = "https://api.exa.ai/contents"


def _read_url() -> str:
    if URL_FILE.exists():
        line = URL_FILE.read_text(encoding="utf-8").strip().splitlines()
        if line:
            return line[0].strip()
    return f"https://hh.ru/resume/{DEFAULT_RESUME_ID}"


def _month_year(d: dict | None) -> str:
    if not isinstance(d, dict):
        return "?"
    y = d.get("year")
    m = d.get("month")
    if y and m:
        return f"{int(m):02d}.{y}"
    if y:
        return str(y)
    return "?"


def _format_hh_resume(data: dict) -> str:
    lines: list[str] = []
    title = (data.get("title") or "").strip()
    if title:
        lines.append(f"**Желаемая должность:** {title}")

    name = " ".join(
        x
        for x in (
            data.get("last_name"),
            data.get("first_name"),
            data.get("middle_name"),
        )
        if x
    ).strip()
    if name:
        lines.append(f"**ФИО:** {name}")

    area = data.get("area")
    if isinstance(area, dict) and area.get("name"):
        lines.append(f"**Город:** {area['name']}")

    total = data.get("total_experience")
    if isinstance(total, dict) and total.get("months"):
        months = int(total["months"])
        lines.append(f"**Опыт:** {months // 12} лет {months % 12} мес.")

    about = (data.get("skills") or data.get("skill_set") or "")
    if isinstance(data.get("skill_set"), list):
        skills = ", ".join(str(s) for s in data["skill_set"] if s)
        if skills:
            lines.append(f"\n## Навыки\n\n{skills}")
    elif isinstance(about, str) and about.strip():
        lines.append(f"\n## Навыки\n\n{about.strip()}")

    desc = (data.get("description") or "").strip()
    if desc:
        lines.append(f"\n## О себе\n\n{desc}")

    exp = data.get("experience")
    if isinstance(exp, list) and exp:
        lines.append("\n## Опыт работы\n")
        for job in exp:
            if not isinstance(job, dict):
                continue
            company = job.get("company") or job.get("employer", {})
            if isinstance(company, dict):
                company = company.get("name") or "?"
            pos = job.get("position") or "?"
            start = _month_year(job.get("start"))
            end = _month_year(job.get("end")) if job.get("end") else "наст. время"
            lines.append(f"### {pos} — {company}")
            lines.append(f"*{start} — {end}*")
            body = (job.get("description") or "").strip()
            if body:
                lines.append("")
                lines.append(body)
            lines.append("")

    edu = data.get("education")
    if isinstance(edu, dict):
        primary = edu.get("primary")
        if isinstance(primary, list) and primary:
            lines.append("\n## Образование\n")
            for item in primary:
                if not isinstance(item, dict):
                    continue
                uni = item.get("name") or "?"
                org = item.get("organization") or item.get("result") or ""
                year = item.get("year") or ""
                lines.append(f"- {uni}" + (f", {org}" if org else "") + (f" ({year})" if year else ""))

    langs = data.get("language")
    if isinstance(langs, list) and langs:
        lines.append("\n## Языки\n")
        for lang in langs:
            if isinstance(lang, dict):
                lines.append(
                    f"- {lang.get('name', '?')}: {lang.get('level', {}).get('name', '?')}"
                    if isinstance(lang.get("level"), dict)
                    else f"- {lang}"
                )

    return "\n".join(lines).strip() + "\n"


def fetch_exa_url(url: str, api_key: str, *, max_characters: int = 20000) -> str:
    """Exa Contents API — только для публично доступных страниц (hh часто таймаутит)."""
    payload = json.dumps(
        {
            "urls": [url],
            "text": {"maxCharacters": max_characters, "includeHtmlTags": False},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        EXA_CONTENTS_API,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Exa API {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Exa сеть: {e}") from e
    results = data.get("results")
    if not isinstance(results, list) or not results:
        raise SystemExit("Exa: пустой ответ (страница не проиндексирована или закрыта)")
    item = results[0]
    if not isinstance(item, dict):
        raise SystemExit("Exa: неверный формат ответа")
    text = (item.get("text") or "").strip()
    if not text:
        raise SystemExit("Exa: нет текста на странице")
    return text


def fetch_hh_resume(resume_id: str, token: str) -> dict:
    url = HH_API.format(resume_id=resume_id)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Copilot/1.0 (resume-import)",
            "Authorization": f"Bearer {token}",
            "HH-User-Agent": "Copilot/1.0 (resume-import)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"hh.ru API {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"hh.ru сеть: {e}") from e


def write_resume_md(body: str, *, source: str, url: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"# Резюме\n\n"
        f"> **Источник:** {url}  \n"
        f"> **Обновлено:** {ts} ({source})\n\n"
        f"Для агента: `@context/resume.md` — опирайся на факты ниже, не выдумывай опыт.\n\n"
        f"---\n\n"
    )
    RESUME_MD.parent.mkdir(parents=True, exist_ok=True)
    RESUME_MD.write_text(header + body.strip() + "\n", encoding="utf-8")
    print(f"OK: {RESUME_MD}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Текстовый файл (копипаст с hh.ru или экспорт)",
    )
    parser.add_argument(
        "--resume-id",
        default=DEFAULT_RESUME_ID,
        help=f"ID резюме на hh.ru (default: {DEFAULT_RESUME_ID})",
    )
    parser.add_argument(
        "--hh-token",
        default=os.environ.get("HH_ACCESS_TOKEN", ""),
        help="OAuth-токен hh.ru (или env HH_ACCESS_TOKEN), см. https://dev.hh.ru",
    )
    parser.add_argument(
        "--exa",
        action="store_true",
        help="Попробовать Exa Contents API (env EXA_API_KEY); для закрытых hh часто не сработает",
    )
    parser.add_argument(
        "--exa-key",
        default=os.environ.get("EXA_API_KEY", ""),
        help="Ключ Exa (или env EXA_API_KEY)",
    )
    args = parser.parse_args()
    url = _read_url()

    if args.hh_token:
        data = fetch_hh_resume(args.resume_id, args.hh_token.strip())
        body = _format_hh_resume(data)
        write_resume_md(body, source="hh.ru API", url=url)
        return 0

    if args.file:
        body = args.file.read_text(encoding="utf-8")
        write_resume_md(body, source=f"file {args.file.name}", url=url)
        return 0

    if not sys.stdin.isatty():
        body = sys.stdin.read()
        if body.strip():
            write_resume_md(body, source="stdin", url=url)
            return 0

    exa_key = (args.exa_key or "").strip()
    if args.exa or exa_key:
        if not exa_key:
            print("Нужен EXA_API_KEY или --exa-key", file=sys.stderr)
            return 1
        try:
            body = fetch_exa_url(url, exa_key)
        except SystemExit as e:
            print(e, file=sys.stderr)
            print(
                "\nExa не обошёл ограничения hh (часто SPA/логин). "
                "Надёжнее: HH_ACCESS_TOKEN или копипаст.\n",
                file=sys.stderr,
            )
            return 1
        write_resume_md(body, source="Exa Contents API", url=url)
        return 0

    print(
        "hh.ru не отдаёт резюме без авторизации.\n\n"
        "Варианты (от надёжного к экспериментальному):\n"
        "  1) HH_ACCESS_TOKEN (dev.hh.ru OAuth) → python scripts/import-resume.py\n"
        "  2) pbpaste | python scripts/import-resume.py\n"
        "  3) python scripts/import-resume.py -f resume.txt\n"
        "  4) EXA_API_KEY=... python scripts/import-resume.py --exa  "
        "(только если резюме открыто всему интернету)\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
