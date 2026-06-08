"""
Tests for football-data.org API mapping functions and fetch task idempotency.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from apps.matches.footballapi import (
    map_status, map_stage, map_points, map_playoff, map_duration,
)


# ---------------------------------------------------------------------------
# map_status
# ---------------------------------------------------------------------------

def test_map_status_scheduled():
    assert map_status('SCHEDULED', None) == 'TBD'

def test_map_status_timed():
    assert map_status('TIMED', None) == 'TBD'

def test_map_status_in_play():
    assert map_status('IN_PLAY', None) == 'IP'

def test_map_status_paused():
    assert map_status('PAUSED', None) == 'IP'

def test_map_status_finished_home_win():
    assert map_status('FINISHED', 'HOME_TEAM') == 'team1'

def test_map_status_finished_away_win():
    assert map_status('FINISHED', 'AWAY_TEAM') == 'team2'

def test_map_status_finished_draw():
    assert map_status('FINISHED', 'DRAW') == 'draw'

def test_map_status_finished_no_winner():
    assert map_status('FINISHED', None) == 'NR'

def test_map_status_postponed():
    assert map_status('POSTPONED', None) == 'NR'

def test_map_status_cancelled():
    assert map_status('CANCELLED', None) == 'NR'

def test_map_status_suspended():
    assert map_status('SUSPENDED', None) == 'NR'


# ---------------------------------------------------------------------------
# map_stage
# ---------------------------------------------------------------------------

def test_map_stage_group_with_letter():
    assert map_stage('GROUP_STAGE', 'GROUP_A') == 'Group A'

def test_map_stage_group_b():
    assert map_stage('GROUP_STAGE', 'GROUP_B') == 'Group B'

def test_map_stage_group_no_group():
    assert map_stage('GROUP_STAGE', None) == 'Group Stage'

def test_map_stage_last_32():
    assert map_stage('LAST_32') == 'Round of 32'

def test_map_stage_last_16():
    assert map_stage('LAST_16') == 'Round of 16'

def test_map_stage_quarter_finals():
    assert map_stage('QUARTER_FINALS') == 'Quarter-final'

def test_map_stage_semi_finals():
    assert map_stage('SEMI_FINALS') == 'Semi-final'

def test_map_stage_third_place():
    assert map_stage('THIRD_PLACE') == 'Third Place'

def test_map_stage_final():
    assert map_stage('FINAL') == 'Final'


# ---------------------------------------------------------------------------
# map_points
# ---------------------------------------------------------------------------

def test_map_points_group():
    assert map_points('GROUP_STAGE') == 1

def test_map_points_r32():
    assert map_points('LAST_32') == 2

def test_map_points_r16():
    assert map_points('LAST_16') == 3

def test_map_points_qf():
    assert map_points('QUARTER_FINALS') == 5

def test_map_points_sf():
    assert map_points('SEMI_FINALS') == 7

def test_map_points_third():
    assert map_points('THIRD_PLACE') == 7

def test_map_points_final():
    assert map_points('FINAL') == 10

def test_map_points_unknown_defaults_to_1():
    assert map_points('UNKNOWN_STAGE') == 1


# ---------------------------------------------------------------------------
# map_playoff
# ---------------------------------------------------------------------------

def test_map_playoff_group_is_false():
    assert map_playoff('GROUP_STAGE') is False

def test_map_playoff_r32_is_true():
    assert map_playoff('LAST_32') is True

def test_map_playoff_r16_is_true():
    assert map_playoff('LAST_16') is True

def test_map_playoff_qf_is_true():
    assert map_playoff('QUARTER_FINALS') is True

def test_map_playoff_sf_is_true():
    assert map_playoff('SEMI_FINALS') is True

def test_map_playoff_third_is_true():
    assert map_playoff('THIRD_PLACE') is True

def test_map_playoff_final_is_true():
    assert map_playoff('FINAL') is True


# ---------------------------------------------------------------------------
# map_duration
# ---------------------------------------------------------------------------

def test_map_duration_regular():
    assert map_duration('REGULAR') == 'REGULAR'

def test_map_duration_extra_time():
    assert map_duration('EXTRA_TIME') == 'EXTRA_TIME'

def test_map_duration_penalty():
    assert map_duration('PENALTY_SHOOTOUT') == 'PENALTY_SHOOTOUT'

def test_map_duration_none():
    assert map_duration(None) is None

def test_map_duration_unknown():
    assert map_duration('UNKNOWN') is None


# ---------------------------------------------------------------------------
# fetch_football_matches task — idempotency
# ---------------------------------------------------------------------------

SAMPLE_MATCH = {
    'id': 999001,
    'utcDate': '2026-06-15T15:00:00Z',
    'status': 'SCHEDULED',
    'stage': 'GROUP_STAGE',
    'group': 'GROUP_A',
    'score': {
        'winner': None,
        'duration': 'REGULAR',
        'fullTime': {'home': None, 'away': None},
    },
    'homeTeam': {'name': 'Argentina', 'tla': 'ARG', 'crest': ''},
    'awayTeam': {'name': 'Brazil', 'tla': 'BRA', 'crest': ''},
}


@pytest.mark.django_db
def test_fetch_football_matches_creates_matches(soccer_tournament):
    soccer_tournament.external_id = 'WC'
    soccer_tournament.save()

    with patch('apps.matches.footballapi.fetch_matches', return_value=[SAMPLE_MATCH]):
        from apps.matches.tasks import fetch_football_matches
        result = fetch_football_matches(soccer_tournament.id)

    from teams.models import Match
    assert Match.objects.filter(match_id='999001').exists()
    assert 'created 1' in result


@pytest.mark.django_db
def test_fetch_football_matches_is_idempotent(soccer_tournament):
    """Running the task twice must not duplicate matches."""
    soccer_tournament.external_id = 'WC'
    soccer_tournament.save()

    with patch('apps.matches.footballapi.fetch_matches', return_value=[SAMPLE_MATCH]):
        from apps.matches.tasks import fetch_football_matches
        fetch_football_matches(soccer_tournament.id)
        fetch_football_matches(soccer_tournament.id)

    from teams.models import Match
    assert Match.objects.filter(match_id='999001').count() == 1


@pytest.mark.django_db
def test_fetch_football_matches_updates_changed_fields(soccer_tournament):
    """Re-running after a kickoff time change updates the stored datetime."""
    soccer_tournament.external_id = 'WC'
    soccer_tournament.save()

    with patch('apps.matches.footballapi.fetch_matches', return_value=[SAMPLE_MATCH]):
        from apps.matches.tasks import fetch_football_matches
        fetch_football_matches(soccer_tournament.id)

    updated = dict(SAMPLE_MATCH)
    updated['utcDate'] = '2026-06-15T18:00:00Z'  # rescheduled 3 h later

    with patch('apps.matches.footballapi.fetch_matches', return_value=[updated]):
        fetch_football_matches(soccer_tournament.id)

    from teams.models import Match
    m = Match.objects.get(match_id='999001')
    assert m.datetime.hour == 18


# ---------------------------------------------------------------------------
# TBD team fallback — null team names in API response
# ---------------------------------------------------------------------------

KNOCKOUT_MATCH_TBD = {
    'id': 999002,
    'utcDate': '2026-07-04T20:00:00Z',
    'status': 'SCHEDULED',
    'stage': 'QUARTER_FINALS',
    'group': None,
    'score': {
        'winner': None,
        'duration': 'REGULAR',
        'fullTime': {'home': None, 'away': None},
    },
    'homeTeam': {'name': None, 'tla': None, 'crest': ''},
    'awayTeam': {'name': None, 'tla': None, 'crest': ''},
}

KNOCKOUT_MATCH_CONFIRMED = {
    **KNOCKOUT_MATCH_TBD,
    'homeTeam': {'name': 'France', 'tla': 'FRA', 'crest': ''},
    'awayTeam': {'name': 'Spain',  'tla': 'ESP', 'crest': ''},
}


@pytest.mark.django_db
def test_fetch_football_matches_creates_tbd_team_when_null(soccer_tournament):
    """Null team name in API response → match created with 'TBD' as team name."""
    soccer_tournament.external_id = 'WC'
    soccer_tournament.save()

    with patch('apps.matches.footballapi.fetch_matches', return_value=[KNOCKOUT_MATCH_TBD]):
        from apps.matches.tasks import fetch_football_matches
        fetch_football_matches(soccer_tournament.id)

    from teams.models import Match, Team
    assert Match.objects.filter(match_id='999002').exists()
    m = Match.objects.get(match_id='999002')
    assert m.team1.name == 'TBD'
    assert m.team2.name == 'TBD'


@pytest.mark.django_db
def test_fetch_football_matches_updates_tbd_to_real_team(soccer_tournament):
    """When API later provides real names, the TBD team record is updated."""
    soccer_tournament.external_id = 'WC'
    soccer_tournament.save()

    with patch('apps.matches.footballapi.fetch_matches', return_value=[KNOCKOUT_MATCH_TBD]):
        from apps.matches.tasks import fetch_football_matches
        fetch_football_matches(soccer_tournament.id)

    with patch('apps.matches.footballapi.fetch_matches', return_value=[KNOCKOUT_MATCH_CONFIRMED]):
        fetch_football_matches(soccer_tournament.id)

    from teams.models import Match
    m = Match.objects.get(match_id='999002')
    assert m.team1.name == 'France'
    assert m.team2.name == 'Spain'
