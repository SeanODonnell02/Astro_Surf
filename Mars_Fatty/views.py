from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from django.conf import settings
import datetime

def root_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return redirect('accounts:login')

@login_required
def home_view(request):
    """
    The new landing page.
    A clean, portfolio-worthy introduction to the AstroSurf application.
    """
    context = {
        'NASA_API_KEY': settings.NASA_API_KEY
    }
    return render(request, 'home.html', context)

@login_required
def mission_control_view(request):
    """
    The old home page, moved to its own dedicated Mission Control dashboard.
    """
    # Fetch ISS data
    iss_data = None
    try:
        iss_response = requests.get("https://api.wheretheiss.at/v1/satellites/25544")
        iss_response.raise_for_status()
        iss_data = iss_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ISS data: {e}")
        iss_data = {'error': 'Could not fetch ISS data.'}

    # Fetch latest Mars Rover photo (Curiosity by default)
    rover_photo = None
    try:
        # Avoid rate limiting by using the public DEMO_KEY or user's key if provided
        nasa_api_key = getattr(settings, 'NASA_API_KEY', 'DEMO_KEY')
        rover_response = requests.get(f"https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/latest_photos?api_key={nasa_api_key}")
        
        # Only process if successful to avoid 429 crashing the page
        if rover_response.status_code == 200:
            rover_photos_data = rover_response.json()
            if rover_photos_data and rover_photos_data.get('latest_photos'):
                rover_photo = rover_photos_data['latest_photos'][0]
        else:
            print(f"Mars Rover API error: {rover_response.status_code}")
            rover_photo = {'error': f"API Error: {rover_response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Mars Rover photo: {e}")
        rover_photo = {'error': 'Could not fetch Mars Rover photo.'}

    context = {
        'iss_data': iss_data,
        'rover_photo': rover_photo,
    }
    return render(request, 'mission_control.html', context)

@login_required
def astro_grav_view(request):
    # Celestial database
    gravity_data = {
        'MERCURY': {'factor': 0.38, 'g': 3.7, 'nasa_url': 'https://science.nasa.gov/mercury/'},
        'VENUS': {'factor': 0.91, 'g': 8.87, 'nasa_url': 'https://science.nasa.gov/venus/'},
        'MOON': {'factor': 0.166, 'g': 1.62, 'nasa_url': 'https://science.nasa.gov/moon/'},
        'MARS': {'factor': 0.38, 'g': 3.71, 'nasa_url': 'https://science.nasa.gov/mars/'},
        'JUPITER': {'factor': 2.34, 'g': 24.79, 'nasa_url': 'https://science.nasa.gov/jupiter/'},
        'SATURN': {'factor': 1.06, 'g': 10.44, 'nasa_url': 'https://science.nasa.gov/saturn/'},
        'URANUS': {'factor': 0.92, 'g': 8.69, 'nasa_url': 'https://science.nasa.gov/uranus/'},
        'NEPTUNE': {'factor': 1.12, 'g': 11.15, 'nasa_url': 'https://science.nasa.gov/neptune/'},
        'PLUTO': {'factor': 0.06, 'g': 0.62, 'nasa_url': 'https://science.nasa.gov/pluto/'},
        'SUN': {'factor': 27.01, 'g': 274.0, 'nasa_url': 'https://science.nasa.gov/sun/'},
        'BLACK_HOLE': {'factor': 1000000.0, 'g': 9800000.0, 'nasa_url': 'https://science.nasa.gov/universe/black-holes/'},
    }

    astro_weight = None
    earth_weight = None
    selected_body = request.POST.get('celestial_body', 'MARS')
    error_message = None

    if request.method == 'POST':
        print(f'EeEeeErrmmm Calculating Astro Gravitational Weight for {selected_body}...')
        weight_str = request.POST.get('earth_weight')
        
        try:
            earth_weight = float(weight_str)
            if selected_body in gravity_data:
                factor = gravity_data[selected_body]['factor']
                astro_weight = round(earth_weight * factor, 2)
            else:
                error_message = "Invalid celestial body selected."
        except (ValueError, TypeError):
            error_message = "Please enter a valid number."
    
    context = {
        'astro_weight': astro_weight,
        'earth_weight': earth_weight,
        'selected_body': selected_body,
        'gravity_data': gravity_data,
        'current_data': gravity_data.get(selected_body),
        'error_message': error_message
    }
    return render(request, 'astro_grav.html', context)

@login_required
def apod_view(request):
    api_key = settings.NASA_API_KEY
    # Allow user to select a date, default to today
    selected_date = request.GET.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    
    api_url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&date={selected_date}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        apod_data = response.json()
    except requests.exceptions.RequestException as e:
        apod_data = {'error': str(e)}
    except Exception as e:
        apod_data = {'error': f"An unexpected error occurred: {e}"}

    return render(request, 'apod.html', {'apod_data': apod_data, 'selected_date': selected_date})

@login_required
def mars_rover_view(request):
    api_key = getattr(settings, 'NASA_API_KEY', 'DEMO_KEY')
    rover = request.GET.get('rover', 'curiosity')
    sol = request.GET.get('sol', '') # Mars day

    # Get the latest photos by default
    if sol:
        api_url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos?sol={sol}&api_key={api_key}"
    else:
        api_url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/latest_photos?api_key={api_key}"

    photos = []
    error = None

    try:
        response = requests.get(api_url)
        
        # Handle rate limiting specifically
        if response.status_code == 429:
            error = "NASA API Rate Limit Exceeded. Please try again later or use a personal API key."
        else:
            response.raise_for_status()
            data = response.json()
            
            if 'photos' in data:
                photos = data['photos']
            elif 'latest_photos' in data:
                photos = data['latest_photos']
            
    except requests.exceptions.RequestException as e:
        if not error: # Don't overwrite the 429 error
            error = str(e)
    except Exception as e:
        error = f"An unexpected error occurred: {e}"

    context = {
        'photos': photos,
        'selected_rover': rover,
        'selected_sol': sol,
        'error': error,
    }
    return render(request, 'mars_rover.html', context)

@login_required
def artemis_view(request):
    """
    Artemis Program Command page.
    Reflects post-Artemis-II reality (flew Apr 1–10, 2026).
    """

    missions = {
        'artemis_i': {
            'name': 'Artemis I',
            'status': 'Complete',
            'launch_date': 'Nov 16, 2022',
            'summary': (
                'Uncrewed flight test of SLS Block 1 and the Orion spacecraft. '
                '25.5-day mission around the Moon. Validated heat shield performance '
                'and end-to-end deep-space hardware.'
            ),
        },
        'artemis_ii': {
            'name': 'Artemis II',
            'status': 'Complete',
            'launch_date': 'Apr 1 – 10, 2026',
            'summary': (
                'First crewed flight of SLS/Orion. Four astronauts on a 10-day '
                'hybrid free-return trajectory around the Moon aboard Orion '
                '"Integrity". Set a new crewed distance record at 252,021 statute '
                'miles — surpassing Apollo 13 by 3,366 miles. Splashed down in '
                'the Pacific; recovered by USS John P. Murtha.'
            ),
        },
        'artemis_iii': {
            'name': 'Artemis III',
            'status': 'Planned',
            'launch_date': '2027',
            'target_date': '2027-06-15T00:00:00Z',
            'summary': (
                'Revised post-Gateway cancellation: crewed low Earth orbit '
                'demonstration of one or both commercial Human Landing Systems '
                '(SpaceX Starship HLS / Blue Origin Blue Moon Mk2). Risk '
                'reduction for lunar surface ops.'
            ),
        },
        'artemis_iv': {
            'name': 'Artemis IV',
            'status': 'Planned',
            'launch_date': 'Early 2028',
            'summary': (
                'First crewed lunar landing since Apollo 17 in 1972. Two '
                'astronauts to the lunar surface via commercial HLS; two '
                'remain in lunar orbit aboard Orion.'
            ),
        },
    }

    crew = [
        {'name': 'Reid Wiseman',    'role': 'COMMANDER',         'agency': 'NASA', 'patch_color': '#00d4ff'},
        {'name': 'Victor Glover',   'role': 'PILOT',             'agency': 'NASA', 'patch_color': '#ff6b35'},
        {'name': 'Christina Koch',  'role': 'MISSION SPECIALIST','agency': 'NASA', 'patch_color': '#00ff88'},
        {'name': 'Jeremy Hansen',   'role': 'MISSION SPECIALIST','agency': 'CSA',  'patch_color': '#ffb800'},
    ]

    diagnostics = [
        {'name': 'SLS Block 1B — Core Stage 2 Integration', 'value': 78, 'status': 'nominal', 'color': 'nominal'},
        {'name': 'Orion EM-3 Crew Module',                  'value': 91, 'status': 'nominal', 'color': 'nominal'},
        {'name': 'SpaceX Starship HLS (Lunar Cfg)',         'value': 64, 'status': 'caution', 'color': 'accent-amber'},
        {'name': 'Blue Origin Blue Moon Mk2',               'value': 42, 'status': 'caution', 'color': 'accent-amber'},
        {'name': 'xEMU Lunar Surface Suits',                'value': 83, 'status': 'nominal', 'color': 'nominal'},
        {'name': 'LC-39B Post-Flight Refit',                'value': 35, 'status': 'critical','color': 'accent-amber'},
    ]

    context = {
        'missions': missions,
        'next_mission': missions['artemis_iii'],
        'active_mission': 'ARTEMIS II · COMPLETE',
        'crew': crew,
        'diagnostics': diagnostics,
    }
    return render(request, 'artemis.html', context)

@login_required
def news_view(request):
    """
    Fetches the latest space news using Spaceflight News API
    """
    news_articles = []
    error = None
    
    try:
        response = requests.get("https://api.spaceflightnewsapi.net/v4/articles/?limit=12")
        response.raise_for_status()
        data = response.json()
        news_articles = data.get('results', [])
    except requests.exceptions.RequestException as e:
        error = "Could not connect to the Spaceflight News network. Please try again later."
        print(f"News API Error: {e}")
        
    context = {
        'articles': news_articles,
        'error': error
    }
    return render(request, 'news.html', context)

@login_required
def games_view(request):
    """
    A page featuring interactive space learning minigames.
    """
    return render(request, 'games.html')
