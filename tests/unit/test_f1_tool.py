"""Tests for the F1 tool."""

from datetime import date

import pytest
import responses

from src.tools.factory import create_tool
from src.tools.implementations.f1 import F1Tool

F1_BASE = "https://f1api.dev/api"


# --- Sample API payloads -------------------------------------------------

DRIVER_STANDINGS = {
    "season": 2026,
    "drivers_championship": [
        {
            "position": 1,
            "points": 100,
            "wins": 3,
            "driver": {
                "name": "Andrea Kimi",
                "surname": "Antonelli",
                "shortName": "ANT",
            },
            "team": {"teamName": "Mercedes"},
        },
        {
            "position": 2,
            "points": 88,
            "wins": 2,
            "driver": {"name": "Max", "surname": "Verstappen", "shortName": "VER"},
            "team": {"teamName": "Red Bull"},
        },
        {
            "position": 3,
            "points": 72,
            "wins": 1,
            "driver": {"name": "Charles", "surname": "Leclerc", "shortName": "LEC"},
            "team": {"teamName": "Ferrari"},
        },
    ],
}

CONSTRUCTOR_STANDINGS = {
    "season": 2026,
    "constructors_championship": [
        {"position": 1, "points": 180, "wins": 4, "team": {"teamName": "Mercedes"}},
        {"position": 2, "points": 150, "wins": 3, "team": {"teamName": "Red Bull"}},
        {"position": 3, "points": 130, "wins": 1, "team": {"teamName": "Ferrari"}},
    ],
}

LAST_RACE = {
    "season": 2026,
    "races": [
        {
            "round": 6,
            "date": "2026-05-03",
            "raceName": "Miami Grand Prix",
            "circuit": {
                "circuitName": "Miami International Autodrome",
                "country": "USA",
            },
            "results": [
                {
                    "position": 1,
                    "time": "1:32:45.123",
                    "driver": {"name": "Andrea Kimi", "surname": "Antonelli"},
                    "team": {"teamName": "Mercedes"},
                },
                {
                    "position": 2,
                    "time": "+3.456",
                    "driver": {"name": "Max", "surname": "Verstappen"},
                    "team": {"teamName": "Red Bull"},
                },
                {
                    "position": 3,
                    "time": "+8.901",
                    "driver": {"name": "Charles", "surname": "Leclerc"},
                    "team": {"teamName": "Ferrari"},
                },
                {
                    "position": 4,
                    "time": "+12.345",
                    "driver": {"name": "Lando", "surname": "Norris"},
                    "team": {"teamName": "McLaren"},
                },
            ],
        }
    ],
}

NEXT_RACE = {
    "season": 2026,
    "round": 7,
    "race": {
        "raceName": "Emilia-Romagna Grand Prix",
        "round": 7,
        "schedule": {
            "race": {"date": "2026-05-17", "time": "13:00:00Z"},
            "qualy": {"date": "2026-05-16", "time": "14:00:00Z"},
            "fp1": {"date": "2026-05-15", "time": "11:30:00Z"},
            "fp2": {"date": "2026-05-15", "time": "15:00:00Z"},
            "fp3": {"date": "2026-05-16", "time": "10:30:00Z"},
            "sprintQualy": {"date": None, "time": None},
            "sprintRace": {"date": None, "time": None},
        },
        "circuit": {
            "circuitName": "Autodromo Enzo e Dino Ferrari",
            "country": "Italy",
            "city": "Imola",
        },
    },
}

NEXT_RACE_SPRINT_WEEKEND = {
    "season": 2026,
    "round": 8,
    "race": {
        "raceName": "Belgian Grand Prix",
        "round": 8,
        "schedule": {
            "race": {"date": "2026-05-24", "time": "13:00:00Z"},
            "qualy": {"date": "2026-05-22", "time": "16:00:00Z"},
            "fp1": {"date": "2026-05-22", "time": "11:30:00Z"},
            "fp2": {"date": "2026-05-23", "time": "10:30:00Z"},
            "fp3": {"date": None, "time": None},
            "sprintQualy": {"date": "2026-05-23", "time": "14:30:00Z"},
            "sprintRace": {"date": "2026-05-24", "time": "10:00:00Z"},
        },
        "circuit": {
            "circuitName": "Circuit de Spa-Francorchamps",
            "country": "Belgium",
            "city": "Spa",
        },
    },
}

LAST_QUALY = {
    "season": 2026,
    "races": {
        "round": 6,
        "raceName": "Miami Grand Prix",
        "qualyDate": "2026-05-02",
        "circuit": {"circuitName": "Miami International Autodrome"},
        "qualyResults": [
            {
                "gridPosition": 1,
                "q1": "1:28.500",
                "q2": "1:28.000",
                "q3": "1:27.798",
                "driver": {"name": "Andrea Kimi", "surname": "Antonelli"},
                "team": {"teamName": "Mercedes"},
            },
            {
                "gridPosition": 2,
                "q1": "1:28.600",
                "q2": "1:28.100",
                "q3": "1:27.900",
                "driver": {"name": "Max", "surname": "Verstappen"},
                "team": {"teamName": "Red Bull"},
            },
            {
                "gridPosition": 3,
                "q1": "1:28.700",
                "q2": "1:28.200",
                "q3": "1:28.050",
                "driver": {"name": "Charles", "surname": "Leclerc"},
                "team": {"teamName": "Ferrari"},
            },
        ],
    },
}

LAST_SPRINT = {
    "season": 2026,
    "races": {
        "round": 8,
        "raceName": "Belgian Grand Prix",
        "circuit": {"circuitName": "Circuit de Spa-Francorchamps"},
        "sprintResults": [
            {
                "position": 1,
                "driver": {"name": "Max", "surname": "Verstappen"},
                "team": {"teamName": "Red Bull"},
            },
            {
                "position": 2,
                "driver": {"name": "Andrea Kimi", "surname": "Antonelli"},
                "team": {"teamName": "Mercedes"},
            },
            {
                "position": 3,
                "driver": {"name": "Lando", "surname": "Norris"},
                "team": {"teamName": "McLaren"},
            },
        ],
    },
}


def _register_core_endpoints():
    """Register the four always-fetched endpoints."""
    responses.add(
        responses.GET,
        f"{F1_BASE}/current/drivers-championship",
        json=DRIVER_STANDINGS,
        status=200,
    )
    responses.add(
        responses.GET,
        f"{F1_BASE}/current/constructors-championship",
        json=CONSTRUCTOR_STANDINGS,
        status=200,
    )
    responses.add(
        responses.GET,
        f"{F1_BASE}/current/last/race",
        json=LAST_RACE,
        status=200,
    )


class TestF1ToolBasics:
    """Initialization and basic behavior."""

    def test_get_name(self):
        tool = F1Tool()
        assert tool.get_name() == "F1"

    def test_default_base_url(self):
        tool = F1Tool()
        assert tool.base_url == F1_BASE


class TestF1ToolOutsideRaceWeekend:
    """Behavior when today is NOT within Fri-Sun of the next race."""

    @responses.activate
    def test_execute_includes_standings_podium_and_next_race(self):
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )

        # Tuesday before the May 17 race — not race weekend
        tool = F1Tool(today=date(2026, 5, 12))
        result = tool.execute({"user_input": "F1"})

        # Driver standings
        assert "DRIVER STANDINGS" in result
        assert "1. Antonelli" in result
        assert "Mercedes" in result
        assert "100" in result  # points

        # Constructor standings
        assert "CONSTRUCTOR STANDINGS" in result
        assert "180" in result

        # Last race podium
        assert "LAST RACE" in result
        assert "Miami Grand Prix" in result
        assert "Antonelli" in result
        assert "Verstappen" in result
        assert "Leclerc" in result
        # Should not include 4th place
        assert "Norris" not in result

        # Next race
        assert "NEXT RACE" in result
        assert "Emilia-Romagna Grand Prix" in result
        assert "Imola" in result
        assert "2026-05-17" in result

        # Outside race weekend — no qualy section
        assert "QUALIFYING" not in result
        assert "SPRINT" not in result

    @responses.activate
    def test_qualy_not_fetched_outside_race_weekend(self):
        """During non-weekend days, the qualy endpoint should not be called."""
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )

        tool = F1Tool(today=date(2026, 5, 12))
        tool.execute({"user_input": "F1"})

        called = [r.request.url for r in responses.calls]
        assert not any("qualy" in u for u in called)
        assert not any("sprint" in u for u in called)


class TestF1ToolRaceWeekend:
    """Behavior when today is within Fri-Sun of the next race."""

    @responses.activate
    def test_includes_qualifying_during_race_weekend(self):
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/qualy",
            json=LAST_QUALY,
            status=200,
        )
        # Non-sprint weekend — sprint endpoint returns 404
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/sprint",
            json={"error": "not found"},
            status=404,
        )

        # Saturday of the Imola race weekend (race is Sunday May 17)
        tool = F1Tool(today=date(2026, 5, 16))
        result = tool.execute({"user_input": "F1"})

        assert "QUALIFYING" in result
        assert "Antonelli" in result
        assert "1:27.798" in result
        # Sprint should not appear since the endpoint 404'd
        assert "SPRINT" not in result

    @responses.activate
    def test_includes_sprint_on_sprint_weekend(self):
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE_SPRINT_WEEKEND,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/qualy",
            json=LAST_QUALY,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/sprint",
            json=LAST_SPRINT,
            status=200,
        )

        # Saturday of Spa sprint weekend (race is Sunday May 24)
        tool = F1Tool(today=date(2026, 5, 23))
        result = tool.execute({"user_input": "F1"})

        assert "SPRINT" in result
        assert "Verstappen" in result
        # Sprint date is provided in next race schedule, indicating sprint weekend
        assert "QUALIFYING" in result

    @responses.activate
    def test_friday_is_in_race_weekend(self):
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/qualy",
            json=LAST_QUALY,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/sprint",
            json={"error": "not found"},
            status=404,
        )

        # Friday of Imola race weekend
        tool = F1Tool(today=date(2026, 5, 15))
        result = tool.execute({"user_input": "F1"})
        assert "QUALIFYING" in result

    @responses.activate
    def test_sunday_is_in_race_weekend(self):
        _register_core_endpoints()
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/qualy",
            json=LAST_QUALY,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/sprint",
            json={"error": "not found"},
            status=404,
        )

        tool = F1Tool(today=date(2026, 5, 17))
        result = tool.execute({"user_input": "F1"})
        assert "QUALIFYING" in result


class TestF1ToolLiveApiShapes:
    """Regression tests for actual f1api.dev response shapes."""

    @responses.activate
    def test_next_race_payload_with_race_as_single_element_list(self):
        """The live API returns `race` as a one-element list, not a dict.

        Previously crashed with: AttributeError: 'list' object has no attribute 'get'
        """
        _register_core_endpoints()

        # Real-world shape: `race` is a list containing one object.
        next_race_as_list = {
            "season": 2026,
            "round": 7,
            "race": [
                {
                    "raceId": "canadian_2026",
                    "raceName": "Formula 1 Lenovo Grand Prix Du Canada 2026",
                    "round": 7,
                    "schedule": {
                        "race": {"date": "2026-05-24", "time": "18:00:00Z"},
                        "qualy": {"date": "2026-05-23", "time": "20:00:00Z"},
                        "fp1": {"date": "2026-05-22", "time": "17:30:00Z"},
                        "fp2": {"date": None, "time": None},
                        "fp3": {"date": None, "time": None},
                        "sprintQualy": {"date": "2026-05-22", "time": "21:00:00Z"},
                        "sprintRace": {"date": "2026-05-23", "time": "16:30:00Z"},
                    },
                    "circuit": {
                        "circuitName": "Circuit Gilles Villeneuve",
                        "country": "Canada",
                        "city": "Montreal",
                    },
                }
            ],
        }
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=next_race_as_list,
            status=200,
        )

        # Tuesday before the weekend — should NOT trip race-weekend logic
        tool = F1Tool(today=date(2026, 5, 19))
        result = tool.execute({"user_input": "F1"})

        assert "NEXT RACE" in result
        assert "Canadian" in result or "Canada" in result
        assert "Round 7" in result
        assert "Montreal" in result
        assert "2026-05-24" in result
        # Sprint date is set in schedule, but we're outside the weekend window
        # so the qualy/sprint endpoints shouldn't be called.
        assert "QUALIFYING" not in result
        assert "SPRINT RESULTS" not in result

    @responses.activate
    def test_race_as_list_during_sprint_weekend(self):
        """`race` as a list AND we are inside the Fri-Sun window of a sprint weekend."""
        _register_core_endpoints()
        next_race_as_list = {
            "season": 2026,
            "round": 7,
            "race": [
                {
                    "raceName": "Canadian Grand Prix",
                    "round": 7,
                    "schedule": {
                        "race": {"date": "2026-05-24", "time": "18:00:00Z"},
                        "qualy": {"date": "2026-05-23", "time": "20:00:00Z"},
                        "sprintQualy": {"date": "2026-05-22", "time": "21:00:00Z"},
                        "sprintRace": {"date": "2026-05-23", "time": "16:30:00Z"},
                    },
                    "circuit": {"circuitName": "Circuit Gilles Villeneuve"},
                }
            ],
        }
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=next_race_as_list,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/qualy",
            json=LAST_QUALY,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/sprint",
            json=LAST_SPRINT,
            status=200,
        )

        # Saturday of the Canadian sprint weekend
        tool = F1Tool(today=date(2026, 5, 23))
        result = tool.execute({"user_input": "F1"})
        assert "QUALIFYING" in result
        assert "SPRINT" in result


class TestF1ToolErrorHandling:
    """Failure modes of the F1 tool."""

    @responses.activate
    def test_standings_failure_returns_error_string(self):
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/drivers-championship",
            json={"error": "server error"},
            status=500,
        )
        # Other endpoints succeed
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/constructors-championship",
            json=CONSTRUCTOR_STANDINGS,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/last/race",
            json=LAST_RACE,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{F1_BASE}/current/next",
            json=NEXT_RACE,
            status=200,
        )

        tool = F1Tool(today=date(2026, 5, 12))
        result = tool.execute({"user_input": "F1"})

        # Driver standings section should mark error but others still appear
        assert "DRIVER STANDINGS" in result
        assert "unavailable" in result.lower() or "error" in result.lower()
        assert "Miami Grand Prix" in result  # last race still rendered
        assert "Emilia-Romagna Grand Prix" in result  # next race still rendered


class TestF1ToolFactory:
    """Factory integration."""

    def test_create_f1_tool_default(self):
        tool = create_tool({"type": "f1"})
        assert isinstance(tool, F1Tool)
        assert tool.base_url == F1_BASE

    def test_create_f1_tool_with_overrides(self):
        tool = create_tool(
            {
                "type": "f1",
                "base_url": "https://example.com/api",
                "request_timeout": 25,
            }
        )
        assert tool.base_url == "https://example.com/api"
        assert tool.request_timeout == 25
