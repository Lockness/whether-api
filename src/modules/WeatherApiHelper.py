import requests
import datetime
from dateutil.parser import parse


class WeatherApiHelper:

    @staticmethod
    def get_weather_at_markers(markers):
        # Get the current UTC time
        now = datetime.datetime.now()

        # Iterate through the markers
        for i in range(0, len(markers)):
            # Make weather query for each coordinate
            url = 'https://api.weather.gov/points/{lat},{lng}/forecast/hourly'.format(
                lat=markers[i]['lat'],
                lng=markers[i]['lng']
            )
            headers = {
                'accept': 'application/geo+json',
                'user-agent': 'locknesssoftware/whether-application'
            }
            r = requests.get(url=url, headers=headers)
            data = r.json()

            # Get utc time from now for marker
            utc_time_from_now = now + datetime.timedelta(minutes=markers[i]['arrival_time'])

            # Iterate over the hourly weather data
            for period in data['properties']['periods']:
                # Convert the start/end time of each period to readable timestamp
                period_start_time = parse(period['startTime']).replace(tzinfo=None)
                period_end_time = parse(period['endTime']).replace(tzinfo=None)

                # If the utc time at the marker is within the period, add the weather data to the marker
                if period_start_time <= utc_time_from_now < period_end_time:
                    markers[i]['weather_data'] = period
                    # Jump to next marker
                    break

        return markers
