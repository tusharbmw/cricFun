from rest_framework import serializers
from teams.models import Team, Match


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'logo_url', 'location']


class MatchSerializer(serializers.ModelSerializer):
    team1 = TeamSerializer(read_only=True)
    team2 = TeamSerializer(read_only=True)
    team1_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team1', write_only=True
    )
    team2_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team2', write_only=True
    )
    result_display = serializers.SerializerMethodField()
    is_live = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'team1', 'team2', 'team1_id', 'team2_id',
            'description', 'venue', 'result', 'result_display',
            'datetime', 'tournament', 'match_id', 'match_points',
            'is_live', 'is_completed', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_result_display(self, obj):
        if obj.result == 'team1' and obj.team1:
            return obj.team1.name
        if obj.result == 'team2' and obj.team2:
            return obj.team2.name
        return obj.get_result_display()
