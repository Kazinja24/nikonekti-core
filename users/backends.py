from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        login_email = email or username or kwargs.get(User.USERNAME_FIELD)
        if not login_email or not password:
            return None

        try:
            user = User.objects.get(email=login_email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
