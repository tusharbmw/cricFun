from datetime import datetime, timezone, timedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from teams.models import Selection, Match
from apps.core.permissions import IsPickOwner
from .serializers import SelectionSerializer, PowerupSerializer, PowerupStatsSerializer

# Powerup budget per season (5 of each)
POWERUP_BUDGET = 5


class PickHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500


def get_powerup_stats(user, tournament_id=None):
    """Return remaining powerup counts for a user, scoped to a tournament."""
    counts = {'hidden': 0, 'fake': 0, 'no_negative': 0}
    qs = Selection.objects.filter(user=user).select_related('match__tournament')
    if tournament_id:
        qs = qs.filter(match__tournament_id=tournament_id)
    for s in qs:
        if s.hidden and not s.match.is_high_stakes:
            counts['hidden'] += 1
        if s.fake:
            counts['fake'] += 1
        if s.no_negative:
            counts['no_negative'] += 1

    return {
        'hidden_count': max(0, POWERUP_BUDGET - counts['hidden']),
        'fake_count': max(0, POWERUP_BUDGET - counts['fake']),
        'no_negative_count': max(0, POWERUP_BUDGET - counts['no_negative']),
    }


class SelectionViewSet(viewsets.ModelViewSet):
    """
    User's match selections (picks).
    - GET /api/v1/picks/          → all my selections
    - POST /api/v1/picks/         → place a pick
    - PUT/PATCH /api/v1/picks/id/ → update selection
    - DELETE /api/v1/picks/id/    → remove selection (only if no powerup applied)
    Custom actions:
    - GET /api/v1/picks/active/       → selections for upcoming/live matches
    - GET /api/v1/picks/history/      → selections for completed matches
    - GET /api/v1/picks/stats/        → powerup stats
    - POST /api/v1/picks/{id}/powerup/ → apply a powerup
    """
    serializer_class = SelectionSerializer
    permission_classes = [IsAuthenticated, IsPickOwner]

    def get_queryset(self):
        return Selection.objects.filter(user=self.request.user).select_related(
            'match', 'match__team1', 'match__team2', 'selection'
        )

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        from apps.users.models import TournamentEnrollment
        match = serializer.validated_data['match']
        if not match.team1 or not match.team2 or not match.team1.name or not match.team2.name or match.team1.name == 'TBD' or match.team2.name == 'TBD':
            raise ValidationError({'match': 'Teams for this match are not yet confirmed.'})
        if not TournamentEnrollment.objects.filter(
            user=self.request.user, tournament=match.tournament
        ).exists():
            raise PermissionDenied('You are not enrolled in this tournament.')
        serializer.save(user=self.request.user, hidden=match.is_high_stakes)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        has_user_powerup = (obj.hidden and not obj.match.is_high_stakes) or obj.fake or obj.no_negative
        if has_user_powerup:
            return Response(
                {'error': "Cannot remove a pick with a powerup applied."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Selections for matches not yet completed, optionally scoped to a tournament."""
        tournament_id = request.query_params.get('tournament') or None
        qs = self.get_queryset().filter(
            Q(match__result='TBD') | Q(match__result='IP') |
            Q(match__result='TOSS') | Q(match__result='DLD')
        )
        if tournament_id:
            qs = qs.filter(match__tournament_id=tournament_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Selections for completed matches, optionally scoped to a tournament.
        Supports ?page_size= up to 500."""
        tournament_id = request.query_params.get('tournament') or None
        qs = self.get_queryset().filter(
            Q(match__result='team1') | Q(match__result='team2') |
            Q(match__result='draw')  | Q(match__result='NR')
        ).order_by('-match__datetime')
        if tournament_id:
            qs = qs.filter(match__tournament_id=tournament_id)
        paginator = PickHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Remaining powerup counts and missing pick count, scoped to a tournament."""
        tournament_id = request.query_params.get('tournament') or None
        powerup_stats = get_powerup_stats(request.user, tournament_id)

        # Missing picks: TBD matches within the pick window without a selection
        from apps.core.models import SiteSettings
        now = datetime.now(timezone.utc)
        window = SiteSettings.get().pick_window_days
        missing_qs = Match.objects.filter(
            result='TBD', datetime__gte=now, datetime__lte=now + timedelta(days=window),
        ).exclude(team1__name='TBD').exclude(team2__name='TBD').exclude(selection__user=request.user)
        if tournament_id:
            missing_qs = missing_qs.filter(tournament_id=tournament_id)
        missing = missing_qs.count()
        urgent_missing = missing_qs.filter(datetime__lte=now + timedelta(hours=24)).count()

        # Remaining matches where powerups can be applied (sport-specific rules)
        remaining_powerup_matches = 0
        if tournament_id:
            from teams.models import Tournament
            try:
                tournament = Tournament.objects.get(pk=tournament_id)
                if tournament.sport == Tournament.Sport.SOCCER:
                    from teams.models import Match as M
                    remaining_powerup_matches = M.objects.filter(
                        tournament_id=tournament_id, result='TBD',
                    ).exclude(description__in=Match._SOCCER_HIGH_STAKES).count()
                else:
                    remaining_powerup_matches = Match.objects.filter(
                        tournament_id=tournament_id, result='TBD', playoff=False,
                    ).count()
            except Tournament.DoesNotExist:
                pass

        return Response({**powerup_stats, 'missing_picks': missing, 'urgent_missing_picks': urgent_missing, 'pick_window_days': window, 'remaining_powerup_matches': remaining_powerup_matches})

    @action(detail=True, methods=['post'])
    def powerup(self, request, pk=None):
        """Toggle a powerup on a selection. POST {powerup_type: 'hidden'|'fake'|'no_negative'}
        Calling with an already-applied powerup removes it (toggle behaviour).
        """
        selection = self.get_object()

        if selection.match.is_high_stakes:
            return Response({'error': 'Powerups are disabled at this stage.'}, status=400)

        serializer = PowerupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        powerup_type = serializer.validated_data['powerup_type']

        # Check match hasn't started
        now = datetime.now(timezone.utc)
        if selection.match.datetime <= now:
            return Response({'error': 'Cannot change powerup after match has started.'}, status=400)

        if getattr(selection, powerup_type):
            # Already applied — remove it (toggle off)
            setattr(selection, powerup_type, False)
            if powerup_type == 'fake':
                selection.fake_selection = None
                selection.fake_draw = False
                selection.save(update_fields=['fake', 'fake_selection', 'fake_draw', 'updated_at'])
            else:
                selection.save(update_fields=[powerup_type, 'updated_at'])
            return Response({'success': f'{powerup_type} powerup removed.'})

        # Check no other powerup is already active on this pick
        all_types = ['hidden', 'fake', 'no_negative']
        if any(getattr(selection, pt) for pt in all_types):
            return Response({'error': 'Remove the existing powerup before applying another.'}, status=400)

        # Check budget
        stats = get_powerup_stats(request.user, selection.match.tournament_id)
        if stats[f'{powerup_type}_count'] <= 0:
            return Response({'error': f'No {powerup_type} powerups remaining.'}, status=400)

        # Soccer group-stage fake powerup: user must specify the decoy (draw is a valid option)
        if powerup_type == 'fake':
            from teams.models import Tournament
            if selection.match.tournament.sport == Tournament.Sport.SOCCER and not selection.match.playoff:
                fake_sel = serializer.validated_data.get('fake_selection_id')
                fake_draw = serializer.validated_data.get('fake_draw', False)
                if not fake_sel and not fake_draw:
                    return Response(
                        {'error': 'Provide fake_selection_id or fake_draw=true for soccer matches.'},
                        status=400,
                    )
                selection.fake_selection = fake_sel
                selection.fake_draw = fake_draw

        setattr(selection, powerup_type, True)
        if powerup_type == 'fake':
            selection.save(update_fields=['fake', 'fake_selection', 'fake_draw', 'updated_at'])
        else:
            selection.save(update_fields=[powerup_type, 'updated_at'])
        return Response({'success': f'{powerup_type} powerup applied.'})
