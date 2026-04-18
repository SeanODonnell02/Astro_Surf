from django.urls import path, include
from django.shortcuts import redirect
from Mars_Fatty import views as mars_views
from whereISS import views as iss_views

urlpatterns = [
    path('', mars_views.home_view, name='home'),
    path('mission-control/', mars_views.mission_control_view, name='mission_control'),
    path('iss-tracker/', iss_views.iss_tracker_view, name='iss_tracker'),
    path('mars-missions/', include('Mars_Fatty.urls', namespace='Mars_Fatty')),
    path('accounts/', include('accounts.urls')),
    path('whereISS/', include('whereISS.urls')),
]