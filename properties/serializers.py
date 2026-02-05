from rest_framework import serializers
from .models import Property


class PropertySerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = ['status', 'created_at']
