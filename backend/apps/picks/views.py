from datetime import datetime, timezone, timedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from teams.models import Selection, Match
from apps.core.permissions import IsPickOwner
from .serializers import SelectionSerializer, PowerupSerializer, PowerupStatsSerializer

# Powerup budget per season (5 of each)
POWERUP_BUDGET = 5

# Match types where powerups are auto-applied as hidden
AUTO_HIDE_TYPES = {'Final', 'Semi Final', 'Qualifier 1', 'Qualifier 2', 'Eliminator', 'Super 8'}

# Whether powerups are currently disabled (playoffs override)
POWERUPS_DISABLED = False  # Set True during playoffs


def get_powerup_stats(user):
    """Return remaining powerup counts for a user."""
    if POWERUPS_DISABLED:
        return {'hidden_count': 0, 'fake_count': 0, 'no_negative_count': 0, 'powerups_disabled': True}

    counts = {'hidden': 0, 'fake': 0, 'no_negative': 0}
    for s in Selection.objects.filter(user=user):
        if s.hidden:
            counts['hidden'] += 1
        if s.fake:
            counts['fake'] += 1
        if s.no_negative:
            counts['no_negative'] += 1

    return {
        'hidden_count': max(0, POWERUP_BUDGET - counts['hidden']),
        'fake_count': max(0, POWERUP_BUDGET - counts['fake']),
        'no_negative_count': max(0, POWERUP_BUDGET - counts['no_negative']),
        'powerups_disabled': False,
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
        match = serializer.validated_data['match']
        hidden = match.description in AUTO_HIDE_TYPES
        serializer.save(user=self.request.user, hidden=hidden)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.hidden or obj.fake or obj.no_negative:
            return Response(
                {'error': "Cannot remove a pick with a powerup applied."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Selections for matches not yet completed."""
        qs = self.get_queryset().filter(
            Q(match__result='TBD') | Q(match__result='IP') |
            Q(match__result='TOSS') | Q(match__result='DLD')
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Selections for completed matches."""
        qs = self.get_queryset().filter(
            Q(match__result='team1') | Q(match__result='team2') | Q(match__result='NR')
        ).order_by('-match__datetime')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Remaining powerup counts and missing pick count."""
        powerup_stats = get_powerup_stats(request.user)

        # Missing picks: TBD matches within the pick window without a selection
        from apps.core.models import SiteSettings
        now = datetime.now(timezone.utc)
        window = SiteSettings.get().pick_window_days
        missing_qs = Match.objects.filter(
            result='TBD', datetime__gte=now, datetime__lte=now + timedelta(days=window)
        ).exclude(selection__user=request.user)
        missing = missing_qs.count()
        urgent_missing = missing_qs.filter(datetime__lte=now + timedelta(hours=24)).count()

        return Response({**powerup_stats, 'missing_picks': missing, 'urgent_missing_picks': urgent_missing, 'pick_window_days': window})

    @action(detail=True, methods=['post'])
    def powerup(self, request, pk=None):
        """Toggle a powerup on a selection. POST {powerup_type: 'hidden'|'fake'|'no_negative'}
        Calling with an already-applied powerup removes it (toggle behaviour).
        """
        selection = self.get_object()

        if POWERUPS_DISABLED:
            return Response({'error': 'Powerups are disabled during playoffs.'}, status=400)

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
            selection.save(update_fields=[powerup_type, 'updated_at'])
            return Response({'success': f'{powerup_type} powerup removed.'})

        # Check no other powerup is already active on this pick
        all_types = ['hidden', 'fake', 'no_negative']
        if any(getattr(selection, pt) for pt in all_types):
            return Response({'error': 'Remove the existing powerup before applying another.'}, status=400)

        # Check budget
        stats = get_powerup_stats(request.user)
        if stats[f'{powerup_type}_count'] <= 0:
            return Response({'error': f'No {powerup_type} powerups remaining.'}, status=400)

        setattr(selection, powerup_type, True)
        selection.save(update_fields=[powerup_type, 'updated_at'])
        return Response({'success': f'{powerup_type} powerup applied.'})
