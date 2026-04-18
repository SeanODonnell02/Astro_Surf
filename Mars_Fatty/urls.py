from django.urls import path
from . import views

app_name = 'Mars_Fatty'

urlpatterns = [
    path('astro-grav/', views.astro_grav_view, name='astro_grav'),
    path('mars-rover/', views.mars_rover_view, name='mars_rover'),
    path('artemis/', views.artemis_view, name='artemis'),
    path('news/', views.news_view, name='news'),
    path('games/', views.games_view, name='games'),
]