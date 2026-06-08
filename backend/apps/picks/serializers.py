from datetime import datetime, timezone, timedelta
from rest_framework import serializers
from teams.models import Selection, Match, Team, Tournament


class SelectionSerializer(serializers.ModelSerializer):
    match_name = serializers.SerializerMethodField()
    match_description = serializers.CharField(source='match.description', read_only=True)
    match_datetime = serializers.DateTimeField(source='match.datetime', read_only=True)
    match_result = serializers.CharField(source='match.result', read_only=True)
    match_result_display = serializers.SerializerMethodField()
    selected_team_name = serializers.CharField(source='selection.name', read_only=True)
    team1_name = serializers.CharField(source='match.team1.name', read_only=True)
    team2_name = serializers.CharField(source='match.team2.name', read_only=True)
    fake_selection_name = serializers.CharField(source='fake_selection.name', read_only=True)

    class Meta:
        model = Selection
        fields = [
            'id', 'match', 'match_name', 'match_description', 'match_datetime',
            'match_result', 'match_result_display',
            'selection', 'selected_team_name', 'team1_name', 'team2_name',
            'draw', 'hidden', 'fake', 'no_negative',
            'fake_selection', 'fake_selection_name', 'fake_draw',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_match_name(self, obj):
        t1 = obj.match.team1.name if obj.match.team1 else '?'
        t2 = obj.match.team2.name if obj.match.team2 else '?'
        return f'{t1} vs {t2}'

    def get_match_result_display(self, obj):
        if obj.match.result == 'team1' and obj.match.team1:
            return obj.match.team1.name
        if obj.match.result == 'team2' and obj.match.team2:
            return obj.match.team2.name
        return obj.match.get_result_display()

    def validate(self, data):
        match = data.get('match') or (self.instance.match if self.instance else None)
        now = datetime.now(timezone.utc)

        if match and match.datetime <= now:
            raise serializers.ValidationError("Cannot place or update a pick after the match has started.")

        from apps.core.models import SiteSettings
        window = SiteSettings.get().pick_window_days
        if match and match.datetime > now + timedelta(days=window):
            raise serializers.ValidationError(f"Picks can only be placed within {window} days of the match.")

        if match and match.result not in ('TBD', 'TOSS'):
            raise serializers.ValidationError("Can only pick on upcoming (TBD) matches.")

        # Duplicate-pick check (only on create, not update)
        if not self.instance and match and 'selection' in data:
            request = self.context.get('request')
            if request and Selection.objects.filter(user=request.user, match=match).exists():
                raise serializers.ValidationError("You already have a pick on this match.")

        # Draw pick validation
        draw = data.get('draw', getattr(self.instance, 'draw', False))
        if draw and match:
            if match.tournament.sport == Tournament.Sport.CRICKET:
                raise serializers.ValidationError({'draw': 'Draw picks are not allowed in cricket.'})
            if match.playoff:
                raise serializers.ValidationError({'draw': 'Draw picks are not allowed in knockout rounds.'})

        return data


class PowerupSerializer(serializers.Serializer):
    powerup_type = serializers.ChoiceField(choices=['hidden', 'fake', 'no_negative'])
    # Soccer fake powerup: user specifies what rivals will see as the decoy
    fake_selection_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), required=False, allow_null=True,
    )
    fake_draw = serializers.BooleanField(required=False, default=False)


class PowerupStatsSerializer(serializers.Serializer):
    hidden_count = serializers.IntegerField()
    fake_count = serializers.IntegerField()
    no_negative_count = serializers.IntegerField()
    powerups_disabled = serializers.BooleanField()
