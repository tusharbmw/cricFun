from rest_framework import serializers
from .models import Team, Match, Selection


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__ALL__'


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = '__ALL__'


class SelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Selection
        fields = '__ALL__'
