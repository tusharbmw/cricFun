from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard),
    path('contact/', views.contact),
    path('teams/', views.teams_view),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register_page, name='register'),
    path('dashboard/', views.dashboard),
    path('schedule/<str:pk>', views.schedule_view),
    path('schedule/', views.schedule_view,name='schedule'),
    path('update/', views.update, name='update'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('maintain/', views.maintain, name='maintain'),
    path('results/', views.results_view, name='results'),
    path('home/', views.home, name='home'),
    path('whatsnew/',views.whatsnew_view, name='whatsnew'),
    path('rules/',views.rules_view, name='rules'),
    path('fill_match/',views.fill_match, name='fill_match'),
    path('api/check/',views.example_view, name ='example_view'),
    path('api/register/',views.register_api_view, name ='register_api_view'),
    path('api/results/', views.results_api_view, name='results_api_view'),
    path('update_powerups/', views.update_powerups, name='update_powerups'),
]