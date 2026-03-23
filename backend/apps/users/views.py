from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer, UserProfileUpdateSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — create new account."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class SocialTokenView(APIView):
    """
    GET /api/v1/auth/social/token/
    Called after Google OAuth redirects back to the React app.
    Reads the allauth Django session and issues JWT tokens for the React app.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        })


class MeView(APIView):
    """GET/PUT /api/v1/auth/me/ — current user profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
