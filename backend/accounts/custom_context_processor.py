from django.contrib.auth.models import User


def user_renderer(request):
    return {
       'all_users': User.objects.all(),
    }