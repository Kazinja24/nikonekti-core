from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        data = super().validate(attrs)

        # Add custom payload
        data["user"] = {
            "id": self.user.id,
            "full_name": self.user.full_name,
            "email": self.user.email,
            "role": self.user.role,
        }

        return data
