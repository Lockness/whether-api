import googlemaps

class GoogleClient:
    def __init__(self):
        self.client = googlemaps.Client(key=os.environ['API_KEY'])
