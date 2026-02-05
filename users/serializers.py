class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'role']
        extra_kwargs = {'password': {'write_only': True}}
