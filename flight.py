import requests
import os
from geopy.distance import geodesic
from math import cos, radians

# Function to convert miles to latitude and longitude deltas
def miles_to_latlon(miles):
    # 1 degree latitude ~ 69 miles
    lat_delta = miles / 69.0
    # 1 degree longitude ~ 69 miles * cos(latitude in radians)
    lon_delta = miles / (69.0 * cos(radians(CENTER[0])))
    return lat_delta, lon_delta

# Parameterize CENTER
CENTER_LAT = float(os.environ["CENTER_LAT"])
CENTER_LON = float(os.environ["CENTER_LON"])
CENTER = (CENTER_LAT, CENTER_LON)

# Calculate BOUNDS as a 1 mile box centered on CENTER
lat_delta, lon_delta = miles_to_latlon(1)
BOUNDS = f"{round(CENTER_LAT + lat_delta, 3)},{round(CENTER_LAT - lat_delta, 3)},{round(CENTER_LON - lon_delta, 3)},{round(CENTER_LON + lon_delta, 3)}"

# Get Bearer token from environment variable
API_KEY = os.getenv("FR24_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Accept-Version": "v1"
}

def get_nearby_flights():
    url = f"https://fr24api.flightradar24.com/api/live/flight-positions/full?bounds={BOUNDS}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return []
    try:
        json_data = response.json()
        # If the response is a list, return it directly
        if isinstance(json_data, list):
            return json_data
        # If the response is a dict, get the 'data' key
        data = json_data.get("data", None)
        if not data:
            return []
        return data
    except Exception as e:
        print(f"Error parsing flight data: {e}")
        return []

def get_airline_name(painted_as):
    url = f"https://fr24api.flightradar24.com/api/static/airlines/{painted_as}/light"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return painted_as
    return response.json().get("name", painted_as)

def get_airport_name(dest_icao):
    url = f"https://fr24api.flightradar24.com/api/static/airports/{dest_icao}/light"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return dest_icao
    return response.json().get("name", dest_icao)

def build_alexa_response():
    flights = get_nearby_flights()

    # Filter planes under 10,000 ft with valid coordinates
    low_flights = [
        f for f in flights
        if f.get("alt") is not None
        and f["alt"] < 50000
        and f.get("lat") is not None
        and f.get("lon") is not None
    ]

    if not low_flights:
        return "There are no low-flying aircraft nearby right now."

    # Find the closest one to the bounding box center
    closest = min(
        low_flights,
        key=lambda f: geodesic(CENTER, (f["lat"], f["lon"])).meters
    )

    flight_number = closest.get("flight", "Unknown flight")
    painted_as = closest.get("painted_as", "unknown")
    dest_icao = closest.get("dest_icao", "an unknown airport")
    aircraft_type = closest.get("type", "an aircraft")

    airline = get_airline_name(painted_as)
    destination = get_airport_name(dest_icao)

    return f"That plane overhead is {airline} flight {flight_number} headed to {destination} in a {aircraft_type}."

if __name__ == "__main__":
    result = build_alexa_response()
    print(result)
