from django.urls import path
from . import views  # The dot means "import views from this exact same folder"

urlpatterns = [
    path('', views.iss_tracker_view, name='iss_tracker'),
]