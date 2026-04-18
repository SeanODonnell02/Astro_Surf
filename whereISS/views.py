from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def iss_tracker_view(request):
    """
    Renders the ISS tracker page.
    All dynamic logic, including geolocation and ISS data fetching,
    is handled by the frontend JavaScript.
    """
    return render(request, 'iss_tracker.html', {})
