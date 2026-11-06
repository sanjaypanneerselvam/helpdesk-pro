from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password2", "phone"]
        extra_kwargs = {"email": {"required": True}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)  # Django's built-in strength rules
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        # Public registration can only ever create a CUSTOMER.
        return User.objects.create_user(role=User.Role.CUSTOMER, **validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if user is None or not user.is_active:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """The logged-in user's own profile. Role cannot be edited here."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "role"]
        read_only_fields = ["id", "username", "role"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    """What an admin sees/edits in /users/. Only role and is_active can change."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "username", "email", "phone", "date_joined"]

    def validate(self, attrs):
        me = self.context["request"].user
        if self.instance and self.instance.pk == me.pk:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError("You cannot deactivate your own account.")
            if "role" in attrs and attrs["role"] != me.role:
                raise serializers.ValidationError("You cannot change your own role.")
        return attrs
