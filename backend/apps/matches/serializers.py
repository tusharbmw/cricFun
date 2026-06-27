from rest_framework import serializers
from teams.models import Match, Team, Tournament


class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = ['id', 'name', 'sport', 'season', 'state', 'external_id']
        read_only_fields = fields


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'logo_url', 'location', 'ranking']


class MatchSerializer(serializers.ModelSerializer):
    team1 = TeamSerializer(read_only=True)
    team2 = TeamSerializer(read_only=True)
    team1_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team1', write_only=True
    )
    team2_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team2', write_only=True
    )
    tournament = TournamentSerializer(read_only=True)
    tournament_id = serializers.PrimaryKeyRelatedField(
        queryset=Tournament.objects.all(), source='tournament', write_only=True
    )
    result_display = serializers.SerializerMethodField()
    allows_draw = serializers.SerializerMethodField()
    is_live = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_high_stakes = serializers.BooleanField(read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'team1', 'team2', 'team1_id', 'team2_id',
            'tournament', 'tournament_id',
            'description', 'venue', 'result', 'result_display',
            'datetime', 'match_id', 'match_points', 'playoff',
            'scores', 'status_text',
            'home_score', 'away_score', 'minute', 'duration', 'odds',
            'allows_draw',
            'is_live', 'is_completed', 'is_high_stakes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_result_display(self, obj):
        if obj.result == 'team1' and obj.team1:
            return obj.team1.name
        if obj.result == 'team2' and obj.team2:
            return obj.team2.name
        return obj.get_result_display()

    def get_allows_draw(self, obj):
        return (
            obj.tournament.sport == Tournament.Sport.SOCCER
            and not obj.playoff
        )
