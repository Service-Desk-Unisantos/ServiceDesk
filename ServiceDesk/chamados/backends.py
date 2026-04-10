from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import MultipleObjectsReturned


class EmailOuUsuarioBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)

        if username is None or password is None:
            return None

        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is not None:
            return user

        UserModel = get_user_model()

        try:
            user = UserModel.objects.get(email__iexact=username)
        except (UserModel.DoesNotExist, MultipleObjectsReturned):
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
