# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
"""Tests for the file-backed exercise state store."""
import pytest
import tempfile
from pathlib import Path

from api.services.exercise_store import ExerciseStore
from api.models.exercise_models import ExerciseState, ExerciseTeam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(name="Test Exercise", phase="setup", **overrides):
    """Factory for minimal ExerciseState instances."""
    defaults = dict(name=name, phase=phase)
    defaults.update(overrides)
    return ExerciseState(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    """ExerciseStore backed by a temporary directory."""
    s = ExerciseStore()
    s._storage_dir = tmp_path / "exercises"
    s._storage_dir.mkdir(parents=True, exist_ok=True)
    s._archive_dir = tmp_path / "exercises" / "archive"
    s._archive_dir.mkdir(parents=True, exist_ok=True)
    return s


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

def test_save_and_get(store):
    """Saved state is retrievable by exercise_id."""
    state = make_state()
    store.save_exercise(state)

    loaded = store.get_exercise(state.exercise_id)
    assert loaded is not None
    assert loaded.exercise_id == state.exercise_id
    assert loaded.name == "Test Exercise"


def test_get_not_found(store):
    """Requesting a non-existent exercise returns None."""
    assert store.get_exercise("does-not-exist") is None


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

def test_version_increments(store):
    """Each save_exercise call bumps the version by one."""
    state = make_state()
    assert state.version == 0

    store.save_exercise(state)
    assert state.version == 1

    store.save_exercise(state)
    assert state.version == 2

    loaded = store.get_exercise(state.exercise_id)
    assert loaded.version == 2


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def test_delete_exercise(store):
    """Deleting an exercise removes it from storage."""
    state = make_state()
    store.save_exercise(state)
    assert store.get_exercise(state.exercise_id) is not None

    deleted = store.delete_exercise(state.exercise_id)
    assert deleted is True
    assert store.get_exercise(state.exercise_id) is None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def test_list_exercises(store):
    """list_exercises returns summaries of all saved exercises."""
    for i in range(3):
        store.save_exercise(make_state(name=f"Ex {i}"))

    summaries = store.list_exercises()
    assert len(summaries) == 3
    assert all("exercise_id" in s for s in summaries)
    assert all("name" in s for s in summaries)


def test_list_filter_by_phase(store):
    """list_exercises(phase=...) filters by exercise phase."""
    store.save_exercise(make_state(name="Setup", phase="setup"))
    store.save_exercise(make_state(name="Active", phase="active"))
    store.save_exercise(make_state(name="Done", phase="completed"))

    active = store.list_exercises(phase="active")
    assert len(active) == 1
    assert active[0]["name"] == "Active"


# ---------------------------------------------------------------------------
# Archiving
# ---------------------------------------------------------------------------

def test_archive_exercise(store):
    """Archiving moves the exercise out of primary storage."""
    state = make_state()
    store.save_exercise(state)
    eid = state.exercise_id

    archive_path = store.archive_exercise(eid)
    assert Path(archive_path).exists()
    # No longer in primary storage
    assert store.get_exercise(eid) is None


# ---------------------------------------------------------------------------
# Version polling
# ---------------------------------------------------------------------------

def test_get_exercise_version(store):
    """get_exercise_version returns the current version without full load."""
    state = make_state()
    store.save_exercise(state)  # version 1
    store.save_exercise(state)  # version 2

    ver = store.get_exercise_version(state.exercise_id)
    assert ver == 2

    # Non-existent exercise returns -1
    assert store.get_exercise_version("ghost") == -1
