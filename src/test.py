import requests
import googlemaps
from datetime import datetime


def get_directions():
    gmaps = googlemaps.Client(key='AIzaSyDQk1fhKAipUizdnXiW9oZkwgpONnrQBZQ')

    now = datetime.now()
    directions_result = gmaps.directions("Ohio State Stadium",
            "Canes Columbus OH",
            mode="driving",
            departure_time=now)

    r = requests.get('http://api.wunderground.com/api/dbb1e59d2b834089/geolookup/hourly/q/OH/Columbus.json')
    if r.status_code == requests.codes.ok:
        parsed_json = r.json()
        location = parsed_json['location']['city']
        temp_f = parsed_json['hourly_forecast'][0]['temp']['english']
        print("Current temperature in %s is: %s" % (location, temp_f))
    else:
        r.raise_for_status()

    print(directions_result)
    return directions_result


def test_endpoint():
    return "Hello"

get_directions()
