from rest_framework import generics, mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdmin
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """POST /auth/register/ - anyone can create a CUSTOMER account."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # ignore any stale token the client may send

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /auth/login/ - returns the token and the user (with role)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    """POST /auth/logout/ - deletes the token so it can't be used again."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."})


class ChangePasswordView(APIView):
    """POST /auth/change-password/ - returns a fresh token (old one is revoked)."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({"detail": "Password changed.", "token": token.key})


class MeView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /auth/me/ - view or edit your own profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin only.
    GET /users/?role=AGENT     list users (optionally filtered by role)
    PATCH /users/{id}/         change role / deactivate
    """

    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = User.objects.all().order_by("id")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role.upper())
        return qs
