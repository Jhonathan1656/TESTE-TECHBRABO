from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import (
    AuthSessionResponseSerializer,
    CurrentUserResponseSerializer,
    LoginRequestSerializer,
)
from apps.core.services import auth_service


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = LoginRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        session = auth_service.start_session(**payload.validated_data)
        return Response(AuthSessionResponseSerializer(session).data)


class LogoutView(APIView):
    def post(self, request):
        auth_service.end_session(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    def get(self, request):
        return Response(CurrentUserResponseSerializer(request.user).data)
