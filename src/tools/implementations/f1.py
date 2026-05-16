"""F1 API tool for Formula 1 standings and race data enrichment."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from ..tool import Tool

logger = logging.getLogger(__name__)


class F1Tool(Tool):
    """Tool to fetch F1 standings, last race, next race, and weekend session data."""

    DEFAULT_BASE_URL = "https://f1api.dev/api"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        request_timeout: int = 10,
        today: Optional[date] = None,
    ):
        """
        Initialize the F1 tool.

        Args:
            base_url: Base URL for the f1api.dev API
            request_timeout: HTTP request timeout in seconds
            today: Override "today" for race-weekend detection (used in tests)
        """
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self._today_override = today

    def get_name(self) -> str:
        return "F1"

    def execute(self, context: Dict[str, Any]) -> str:
        today = self._today_override or date.today()

        driver_standings = self._safe_fetch(
            f"{self.base_url}/current/drivers-championship"
        )
        constructor_standings = self._safe_fetch(
            f"{self.base_url}/current/constructors-championship"
        )
        last_race = self._safe_fetch(f"{self.base_url}/current/last/race")
        next_race = self._safe_fetch(f"{self.base_url}/current/next")

        sections: List[str] = []
        sections.append(self._format_driver_standings(driver_standings))
        sections.append(self._format_constructor_standings(constructor_standings))
        sections.append(self._format_last_race_podium(last_race))
        sections.append(self._format_next_race(next_race))

        if self._is_race_weekend(next_race, today):
            qualy = self._safe_fetch(f"{self.base_url}/current/last/qualy")
            sections.append(self._format_qualifying(qualy))

            if self._is_sprint_weekend(next_race):
                sprint = self._safe_fetch(f"{self.base_url}/current/last/sprint")
                sprint_section = self._format_sprint(sprint)
                if sprint_section:
                    sections.append(sprint_section)

        return "\n\n".join(s for s in sections if s)

    # --- HTTP --------------------------------------------------------------

    def _safe_fetch(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:  # noqa: BLE001 — surface upstream failures gracefully
            logger.warning(f"F1 API request failed for {url}: {e}")
            return None

    # --- Race weekend detection -------------------------------------------

    def _is_race_weekend(
        self, next_race_payload: Optional[Dict[str, Any]], today: date
    ) -> bool:
        race_date = self._extract_next_race_date(next_race_payload)
        if not race_date:
            return False
        # Race is Sunday; weekend window is Fri (-2) through Sun (race day).
        weekend_start = race_date - timedelta(days=2)
        return weekend_start <= today <= race_date

    def _is_sprint_weekend(self, next_race_payload: Optional[Dict[str, Any]]) -> bool:
        race = (next_race_payload or {}).get("race") or {}
        schedule = race.get("schedule") or {}
        sprint_race = schedule.get("sprintRace") or {}
        return bool(sprint_race.get("date"))

    def _extract_next_race_date(
        self, next_race_payload: Optional[Dict[str, Any]]
    ) -> Optional[date]:
        race = (next_race_payload or {}).get("race") or {}
        schedule = race.get("schedule") or {}
        race_block = schedule.get("race") or {}
        date_str = race_block.get("date")
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Unparseable next race date: {date_str}")
            return None

    # --- Formatters -------------------------------------------------------

    def _format_driver_standings(self, payload: Optional[Dict[str, Any]]) -> str:
        header = "DRIVER STANDINGS (current season):"
        if not payload:
            return f"{header}\n- unavailable"
        rows = payload.get("drivers_championship") or []
        if not rows:
            return f"{header}\n- unavailable"

        lines = [header]
        for entry in rows[:10]:
            position = entry.get("position", "?")
            points = entry.get("points", 0)
            wins = entry.get("wins", 0)
            driver = entry.get("driver") or {}
            team = entry.get("team") or {}
            surname = driver.get("surname") or ""
            given = driver.get("name") or ""
            team_name = team.get("teamName") or ""
            lines.append(
                f"{position}. {surname} ({given}) — {team_name} — {points} pts, {wins} wins"
            )
        return "\n".join(lines)

    def _format_constructor_standings(self, payload: Optional[Dict[str, Any]]) -> str:
        header = "CONSTRUCTOR STANDINGS (current season):"
        if not payload:
            return f"{header}\n- unavailable"
        rows = payload.get("constructors_championship") or []
        if not rows:
            return f"{header}\n- unavailable"

        lines = [header]
        for entry in rows:
            position = entry.get("position", "?")
            points = entry.get("points", 0)
            wins = entry.get("wins", 0)
            team = entry.get("team") or {}
            team_name = team.get("teamName") or ""
            lines.append(f"{position}. {team_name} — {points} pts, {wins} wins")
        return "\n".join(lines)

    def _format_last_race_podium(self, payload: Optional[Dict[str, Any]]) -> str:
        header = "LAST RACE PODIUM:"
        race = self._first_race(payload)
        if not race:
            return f"{header}\n- unavailable"

        race_name = race.get("raceName") or "Unknown race"
        race_date = race.get("date") or ""
        circuit = (race.get("circuit") or {}).get("circuitName") or ""

        lines = [header, f"{race_name} ({race_date}) — {circuit}".strip(" —")]

        results = race.get("results") or []
        for entry in results[:3]:
            position = entry.get("position", "?")
            time_str = entry.get("time") or ""
            driver = entry.get("driver") or {}
            team = entry.get("team") or {}
            surname = driver.get("surname") or ""
            team_name = team.get("teamName") or ""
            lines.append(f"{position}. {surname} ({team_name}) {time_str}".rstrip())
        return "\n".join(lines)

    def _format_next_race(self, payload: Optional[Dict[str, Any]]) -> str:
        header = "NEXT RACE:"
        if not payload:
            return f"{header}\n- unavailable"
        race = payload.get("race") or {}
        if not race:
            return f"{header}\n- unavailable"

        name = race.get("raceName") or "Unknown"
        round_no = race.get("round") or payload.get("round")
        schedule = race.get("schedule") or {}
        race_block = schedule.get("race") or {}
        race_date = race_block.get("date") or ""
        race_time = race_block.get("time") or ""
        circuit = race.get("circuit") or {}
        circuit_name = circuit.get("circuitName") or ""
        city = circuit.get("city") or ""
        country = circuit.get("country") or ""
        location = ", ".join(p for p in [city, country] if p)

        lines = [
            header,
            f"Round {round_no}: {name}",
            f"Date: {race_date} {race_time}".strip(),
            f"Circuit: {circuit_name}" + (f" — {location}" if location else ""),
        ]

        qualy_block = schedule.get("qualy") or {}
        if qualy_block.get("date"):
            lines.append(
                f"Qualifying: {qualy_block.get('date')} {qualy_block.get('time') or ''}".strip()
            )
        sprint_block = schedule.get("sprintRace") or {}
        if sprint_block.get("date"):
            lines.append(
                f"Sprint: {sprint_block.get('date')} {sprint_block.get('time') or ''}".strip()
            )
        return "\n".join(lines)

    def _format_qualifying(self, payload: Optional[Dict[str, Any]]) -> str:
        header = "QUALIFYING (most recent session):"
        race = self._race_block(payload)
        if not race:
            return f"{header}\n- unavailable"

        race_name = race.get("raceName") or ""
        results = race.get("qualyResults") or []
        if not results:
            return f"{header}\n- unavailable"

        lines = [header, f"{race_name}".strip()]
        for entry in results[:10]:
            grid = entry.get("gridPosition", "?")
            driver = entry.get("driver") or {}
            team = entry.get("team") or {}
            surname = driver.get("surname") or ""
            team_name = team.get("teamName") or ""
            q3 = entry.get("q3") or entry.get("q2") or entry.get("q1") or ""
            lines.append(f"{grid}. {surname} ({team_name}) {q3}".rstrip())
        return "\n".join(lines)

    def _format_sprint(self, payload: Optional[Dict[str, Any]]) -> Optional[str]:
        race = self._race_block(payload)
        if not race:
            return None
        results = race.get("sprintResults") or []
        if not results:
            return None

        header = "SPRINT RESULTS (most recent session):"
        race_name = race.get("raceName") or ""
        lines = [header, f"{race_name}".strip()]
        for entry in results[:8]:
            position = entry.get("position", "?")
            driver = entry.get("driver") or {}
            team = entry.get("team") or {}
            surname = driver.get("surname") or ""
            team_name = team.get("teamName") or ""
            lines.append(f"{position}. {surname} ({team_name})")
        return "\n".join(lines)

    # --- Payload helpers --------------------------------------------------

    def _first_race(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Return the first race from a `races` list payload."""
        if not payload:
            return None
        races = payload.get("races")
        if isinstance(races, list) and races:
            return races[0]
        if isinstance(races, dict):
            return races
        return None

    def _race_block(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Return the race object for qualy/sprint payloads (races may be dict or list)."""
        if not payload:
            return None
        races = payload.get("races")
        if isinstance(races, dict):
            return races
        if isinstance(races, list) and races:
            return races[0]
        return None
