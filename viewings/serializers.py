from rest_framework import serializers
from .models import Viewing


class ViewingSerializer(serializers.ModelSerializer):
    tenant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Viewing
        fields = '__all__'
        read_only_fields = ['status', 'created_at']
