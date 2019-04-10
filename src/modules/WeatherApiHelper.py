import asyncio
import datetime

import aiohttp
from dateutil.parser import parse


class WeatherApiHelper:

    def __init__(self):
        self.BASE_URL = 'https://api.weather.gov/points/{lat},{lng}/forecast/hourly'

    async def get_response(self, session, marker):
        url = self.BASE_URL.format(
            lat=marker['lat'],
            lng=marker['lng']
        )
        async with session.get(url) as resp:
            data = await resp.json()
        return data

    async def download_one(self, marker):
        base_headers = {
            'accept': 'application/geo+json',
            'user-agent': 'locknesssoftware/whether-application'
        }
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False), headers=base_headers) as session:
            data = await self.get_response(session, marker)
        return data, marker

    def get_weather_at_markers(self, markers):
        loop = asyncio.get_event_loop()
        to_do = [self.download_one(marker) for marker in markers]
        wait_coro = asyncio.wait(to_do)
        res, _ = loop.run_until_complete(wait_coro)
        now = datetime.datetime.now()

        markers = []
        for response in res:
            weather_response, marker = response.result()
            # marker = response.result()[1]
            utc_time_from_now = now + datetime.timedelta(minutes=marker['arrival_time'])

            for period in weather_response['properties']['periods']:
                period_start_time = parse(period['startTime']).replace(tzinfo=None)
                period_end_time = parse(period['endTime']).replace(tzinfo=None)

                # If the utc time at the marker is within the period, add the weather data to the marker
                if period_start_time <= utc_time_from_now < period_end_time:
                    marker['weather_data'] = period
                    markers.append(marker)
                    # Jump to next marker
                    break
        return markers
