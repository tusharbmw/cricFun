from django.db.models import Q
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from teams.models import Team, Match
from apps.core.permissions import IsAdminOrReadOnly
from .serializers import MatchSerializer, TeamSerializer


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of teams."""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'location']


class MatchViewSet(viewsets.ModelViewSet):
    """
    Matches endpoint.
    - List/retrieve: all authenticated users
    - Create/update/delete: admin only
    Custom actions: /live/, /upcoming/, /completed/
    """
    queryset = Match.objects.select_related('team1', 'team2').all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['result', 'tournament']
    search_fields = ['description', 'venue', 'team1__name', 'team2__name']
    ordering_fields = ['datetime', 'match_points']
    ordering = ['datetime']

    @action(detail=False, methods=['get'])
    def live(self, request):
        """Currently live matches (result=IP/TOSS/DLD)."""
        qs = self.get_queryset().filter(
            Q(result='IP') | Q(result='TOSS') | Q(result='DLD')
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Upcoming matches (result=TBD), next 10."""
        qs = self.get_queryset().filter(result='TBD')[:10]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Completed matches (team1/team2/NR won), no pagination."""
        qs = self.get_queryset().filter(
            Q(result='team1') | Q(result='team2') | Q(result='NR')
        ).order_by('-datetime')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def selections(self, request, pk=None):
        """
        Show all selections for a match.
        - Before match starts (TBD): hidden picks are masked; fake/Googly picks show opposite team.
        - Once match is locked (IP/TOSS/DLD/completed): all real picks are revealed.
        Own picks are always shown correctly regardless of powerup.
        """
        match = self.get_object()
        # Reveal real picks as soon as match is no longer TBD (locked/live/completed)
        is_locked = match.result != 'TBD'

        sel1_users = []
        sel2_users = []
        hidden_count = 0

        for s in match.selection_set.select_related('user', 'selection').all():
            is_own = s.user_id == request.user.id

            if not is_locked and not is_own:
                # Hidden: mask entirely — show in hidden bucket
                if s.hidden:
                    hidden_count += 1
                    continue
                # Googly/Fake: show opposite team as decoy
                if s.fake:
                    if s.selection == match.team1:
                        sel2_users.append(s.user.username)
                    elif s.selection == match.team2:
                        sel1_users.append(s.user.username)
                    continue

            # Own pick, or match locked: always show real pick
            if s.selection == match.team1:
                sel1_users.append(s.user.username)
            elif s.selection == match.team2:
                sel2_users.append(s.user.username)

        return Response({
            'match_id': match.id,
            'team1': match.team1.name if match.team1 else None,
            'team2': match.team2.name if match.team2 else None,
            'team1_selections': sel1_users,
            'team1_count': len(sel1_users),
            'team2_selections': sel2_users,
            'team2_count': len(sel2_users),
            'hidden_count': hidden_count,
        })
