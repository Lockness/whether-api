import googlemaps

import constants as c


class GoogleClient:
    def __init__(self):
        self.client = googlemaps.Client(key=c.api_key)
