from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Password doesnt match")
        return attrs

    def create(self, validated_data: dict):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "password_confirm"]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    has_verified_email = serializers.SerializerMethodField()

    def get_has_verified_email(self, obj):
        return obj.is_verified

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "role",
            "is_online", "last_seen", "is_active", "is_verified", "hase_verified_email",
            "email_verified_at", "created_at", "updated_at",
        ] # fmt: skip


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
