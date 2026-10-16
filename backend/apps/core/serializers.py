from rest_framework import serializers

from apps.core.roles import find_user_roles
from apps.core.services.auth_service import find_display_name


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class CurrentUserResponseSerializer(serializers.Serializer):
    username = serializers.CharField(source="get_username")
    display_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_display_name(self, user) -> str:
        return find_display_name(user)

    def get_roles(self, user) -> list[str]:
        return sorted(role.value for role in find_user_roles(user))


class AuthSessionResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = CurrentUserResponseSerializer()


class UserSummaryResponseSerializer(serializers.Serializer):
    username = serializers.CharField(source="get_username")
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, user) -> str:
        return find_display_name(user)
