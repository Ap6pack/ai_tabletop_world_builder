#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the DB-backed ScenarioLibraryService."""

import pytest

from api.services.scenario_library_service import ScenarioLibraryService


@pytest.fixture
def library():
    return ScenarioLibraryService()


def _sample():
    return {
        "name": "Ransomware Drill",
        "description": "A ransomware incident-response exercise",
        "industry": "Financial Services",
        "difficulty": "advanced",
        "category": "incident-response",
        "tags": ["ransomware", "recovery"],
    }


def test_add_and_get(library):
    added = library.add_to_library(_sample(), author="alice")
    assert added["id"]
    fetched = library.get_scenario(added["id"])
    assert fetched is not None
    assert fetched["name"] == "Ransomware Drill"
    assert fetched["author"] == "alice"


def test_list_and_filter(library):
    library.add_to_library(_sample())
    library.add_to_library({**_sample(), "difficulty": "beginner"})
    assert len(library.list_scenarios()) == 2
    assert len(library.list_scenarios(difficulty="advanced")) == 1


def test_rate_updates_average(library):
    added = library.add_to_library(_sample())
    library.rate_scenario(added["id"], 5, user_id="u1")
    result = library.rate_scenario(added["id"], 3, user_id="u2")
    assert result["rating_count"] == 2
    assert result["rating"] == 4.0


def test_fork_creates_independent_copy(library):
    added = library.add_to_library(_sample())
    forked = library.fork_scenario(added["id"], user_id="bob")
    assert forked["id"] != added["id"]
    assert forked["original_id"] == added["id"]
    assert forked["author"] == "bob"
    assert forked["visibility"] == "private"


def test_search(library):
    library.add_to_library(_sample())
    assert len(library.search_scenarios("ransomware")) == 1
    assert len(library.search_scenarios("nonexistent-term")) == 0


def test_templates_are_available(library):
    # Built-in templates remain static seed files, not database rows.
    templates = library.get_templates()
    assert len(templates) >= 5
    assert all("id" in t and "name" in t for t in templates)
