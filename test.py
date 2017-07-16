import json
import requests, json
import googlemaps
from datetime import datetime

gmaps = googlemaps.Client(key='AIzaSyAzoD6R1OJhUvM3gVSsBXuEucOMPbEjuM4')

#Geocoding an address
#geocode_result = gmaps.geocode('1600 Amphitheatre Parkway, Mountain View, CA')
#print(geocode_result)

#Look up an address with reverse geocoding

#Requesting directions via public transit
now = datetime.now()
directions_result = gmaps.directions("Ohio State Stadium",
        "Canes Columbus OH",
        mode="driving",
        departure_time=now)

print(directions_result)



r = requests.get('http://api.wunderground.com/api/dbb1e59d2b834089/geolookup/hourly/q/OH/Columbus.json')

if r.status_code == requests.codes.ok:
    parsed_json = r.json() 
    location = parsed_json['location']['city']
    temp_f = parsed_json['hourly_forecast'][0]['temp']['english']
    print("Current temperature in %s is: %s" % (location, temp_f))
else:
    bad_r.raise_for_status()

