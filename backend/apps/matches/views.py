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
        """Upcoming matches (result=TBD), paginated by offset/limit."""
        limit  = min(int(request.query_params.get('limit', 10)), 50)
        offset = max(int(request.query_params.get('offset', 0)), 0)
        qs     = self.get_queryset().filter(result='TBD')
        total  = qs.count()
        page   = qs[offset:offset + limit]
        serializer = self.get_serializer(page, many=True)
        return Response({
            'results':  serializer.data,
            'count':    total,
            'has_more': (offset + limit) < total,
        })

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Completed matches (team1/team2/NR won), no pagination."""
        qs = self.get_queryset().filter(
            Q(result='team1') | Q(result='team2') | Q(result='NR')
        ).order_by('-datetime')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def team_form(self, request, pk=None):
        """
        For each team: last 5 form results + season stats in this tournament.
        Also returns head-to-head history between the two teams in this tournament.
        """
        match = self.get_object()
        tournament = match.tournament

        def get_form(team):
            if not team:
                return []
            recent = (
                Match.objects
                .filter(Q(team1=team) | Q(team2=team), result__in=['team1', 'team2', 'NR'])
                .exclude(pk=match.pk)
                .select_related('team1', 'team2')
                .order_by('-datetime')[:5]
            )
            form = []
            for m in recent:
                opponent = m.team2.name if m.team1 == team else m.team1.name
                if m.result == 'NR':
                    outcome = 'N'
                elif (m.result == 'team1' and m.team1 == team) or (m.result == 'team2' and m.team2 == team):
                    outcome = 'W'
                else:
                    outcome = 'L'
                form.append({'result': outcome, 'opponent': opponent, 'date': m.datetime.isoformat()})
            return form

        def get_season_stats(team):
            if not team:
                return None
            qs = Match.objects.filter(
                Q(team1=team) | Q(team2=team),
                result__in=['team1', 'team2', 'NR'],
            )
            won = qs.filter(
                Q(result='team1', team1=team) | Q(result='team2', team2=team)
            ).count()
            lost = qs.filter(
                Q(result='team1', team2=team) | Q(result='team2', team1=team)
            ).count()
            return {'played': won + lost, 'won': won, 'lost': lost}

        def get_h2h():
            if not match.team1 or not match.team2:
                return []
            qs = (
                Match.objects
                .filter(
                    Q(team1=match.team1, team2=match.team2) | Q(team1=match.team2, team2=match.team1),
                    result__in=['team1', 'team2', 'NR'],
                )
                .select_related('team1', 'team2')
                .order_by('-datetime')
            )
            results = []
            for m in qs:
                if m.result == 'NR':
                    winner = None
                elif m.result == 'team1':
                    winner = m.team1.name
                else:
                    winner = m.team2.name
                results.append({
                    'date': m.datetime.isoformat(),
                    'description': m.description or '',
                    'winner': winner,
                })
            return results

        return Response({
            'team1':         match.team1.name if match.team1 else None,
            'team2':         match.team2.name if match.team2 else None,
            'team1_form':    get_form(match.team1),
            'team2_form':    get_form(match.team2),
            'team1_season':  get_season_stats(match.team1),
            'team2_season':  get_season_stats(match.team2),
            'h2h':           get_h2h(),
        })

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
        is_locked = match.result not in ('TBD', 'TOSS')

        sel1_users = []
        sel2_users = []
        hidden_count = 0
        powerups = {}  # {username: 'hidden'|'fake'|'no_negative'} — only populated when locked

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

            # Record which powerplay (if any) was used — only revealed once locked
            if is_locked:
                if s.hidden:
                    powerups[s.user.username] = 'hidden'
                elif s.fake:
                    powerups[s.user.username] = 'fake'
                elif s.no_negative:
                    powerups[s.user.username] = 'no_negative'

        return Response({
            'match_id': match.id,
            'team1': match.team1.name if match.team1 else None,
            'team2': match.team2.name if match.team2 else None,
            'team1_selections': sel1_users,
            'team1_count': len(sel1_users),
            'team2_selections': sel2_users,
            'team2_count': len(sel2_users),
            'hidden_count': hidden_count,
            'powerups': powerups,
        })
