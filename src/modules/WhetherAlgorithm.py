import datetime
import math

import googlemaps
import numpy as np
from dateutil.parser import parse
from pytz import timezone

import src.constants as c
from src.modules.AsyncHelper import AsyncHelper
from src.modules.GoogleClient import GoogleClient


class WhetherAlgorithm:
    def __init__(self):
        self.googlemaps_client = GoogleClient().client

    def get_directions(self, params, waypoints=None, origin=None):
        """
        Queries the googlemaps api for directions between an origin and destination.

        :param params: TODO
        :param waypoints: points to alter route
        :param origin: starting point of direction

        :return: list of routes
        """
        optimize_waypoints = True
        if waypoints is not None:
            optimize_waypoints = False

        if origin is None:
            origin = params['origin']

        result = self.googlemaps_client.directions(origin,
                                                   params['destination'],
                                                   mode='driving',
                                                   departure_time=datetime.datetime.now(),
                                                   waypoints=waypoints,
                                                   optimize_waypoints=optimize_waypoints)
        return result

    @staticmethod
    def extract_polylines(directions_result):
        """
        Takes polyline points and converts to list of lat/lng dicts

        :param directions_result: TODO

        :return: list of dicts with lat/lng keys
        """
        all_points = []

        for step in directions_result[0]['legs'][0]['steps']:
            polyline_points = step['polyline']['points']
            decoded_points = googlemaps.convert.decode_polyline(polyline_points)

            # need to keep first point if start of list, otherwise first point is a duplicate
            if not all_points:
                all_points = decoded_points
            else:
                all_points.extend(decoded_points[1:])

        return all_points

    def get_equidistant_markers_from_polyline_points(self, points, distance):
        """
        Given set of points, returns set of points that are evenly spaced along
        said points.

        Drops last point if close enough to destination.

        Order is guaranteed unless if statement is entered. TODO: fix that.

        Essentially, builds array of distances between points, and uses a binary search to determine
        where to insert along the array (numpy.searchsorted). Then uses remainder to determine how far
        along a polyline to travel for each evenly spaced point.

        :param points: list of dict coords of lat/long
        :param distance: distance between points, in km
        :return: list of dict of coords lat/long
        """
        # from dict to array
        points = np.array([list(d.values()) for d in points])

        # build array of sequential points
        sequ_points = np.empty((len(points) - 1, 4))
        sequ_points[:, :2] = points[:-1]
        sequ_points[:, 2:] = points[1:]

        # calculate distances between points, and figure out remainders
        distances = np.apply_along_axis(WhetherAlgorithm.haversine, 1, sequ_points)
        mods = (distances.cumsum() % distance)

        # get steps: start at distance, with step of distance until end
        steps = np.arange(distance, distances.sum(), distance)

        # locations where steps insert
        inserts = np.searchsorted(distances.cumsum(), steps) - 1

        # check distance between last insert and destination
        # ignores remainder, so it's an approximation
        distance_bewteen_last = distances[inserts[-1] + 1:].sum()

        # if small enough distance, drop last step and redo
        if distance_bewteen_last < distance / 2:
            steps = steps[:-1]
            inserts = np.searchsorted(distances.cumsum(), steps) - 1

        # look for duplicates
        uns, idxs, cnts = np.unique(inserts, return_index=True, return_counts=True)

        # append remainders to tweeners in order to np apply
        tweeners = sequ_points[uns + 1]
        remainders = (distance - mods[uns])

        # look for and process duplicates
        m_dup = (cnts > 1).nonzero()[0]

        # TODO: the points generated here don't look optimal, figure it out
        # only called if len of polyline is greater than requested distance between points
        if len(m_dup) > 0:
            dups, count = uns[m_dup], cnts[m_dup]-1

            dups = np.repeat(dups, count)
            ins = np.repeat(idxs[m_dup]+1, count)

            ar1 = lambda x: np.arange(start=1, stop=x+1)
            count = np.concatenate(np.array(list(map(ar1, count))))

            more_tweeners = sequ_points[dups + 1]
            more_remainders = ((distance * count) + mods[dups])

            # combine
            tweeners = np.vstack((tweeners, more_tweeners))
            remainders = np.hstack((remainders, more_remainders))

        merged = np.concatenate((tweeners, remainders[:, np.newaxis]), axis=1)

        # points
        even_points = np.apply_along_axis(WhetherAlgorithm.move_towards, 1, merged)

        # back into dict
        list_dict_even_points = [{'lat': lat, 'lng': lng} for lat, lng in even_points]

        # add first and last points
        list_dict_even_points = [{'lat': points[0][0], 'lng': points[0][1]}] + \
                                list_dict_even_points + \
                                [{'lat': points[-1][0], 'lng': points[-1][1]}]

        return list_dict_even_points

    @staticmethod
    def move_towards(coords_dist):
        """
        Moves along a line segment by the specified distance

        :param coords_dist: iterable of [lat1, lon1, lat2, lon2, distance]
        :return: new coordinate
        """
        # expand
        lat1, lon1, lat2, lon2, distance = coords_dist

        # Convert degrees to radians
        d_lon = math.radians(lon2 - lon1)
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)

        # Find the bearing from point1 to point2
        bearing = math.atan2(math.sin(d_lon) * math.cos(lat2),
                             math.cos(lat1) * math.sin(lat2) -
                             math.sin(lat1) * math.cos(lat2) *
                             math.cos(d_lon))

        # Earth's radius in miles
        ang_dist = distance / 3959

        # Calculate the destination point, given the source and bearing
        lat2 = math.asin(math.sin(lat1) * math.cos(ang_dist) +
                         math.cos(lat1) * math.sin(ang_dist) *
                         math.cos(bearing))

        lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(ang_dist) *
                                 math.cos(lat1),
                                 math.cos(ang_dist) - math.sin(lat1) *
                                 math.sin(lat2))

        if math.isnan(lat2) or math.isnan(lon2):
            return None

        return np.array([math.degrees(lat2), math.degrees(lon2)])

    @staticmethod
    def haversine(coords):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)

        :param coords: iterable of [lat1, lon1, lat2, lon2]
        :return: distance in miles
        """
        lat1, lon1, lat2, lon2 = coords

        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers is 3,959 miles
        miles = 3959 * c

        return miles

    @staticmethod
    def create_waypoint_string(waypoints):
        waypoints_joined = []
        for waypoint in waypoints:
            waypoints_joined.append(str(waypoint['lat']) + ',' + str(waypoint['lng']))

        return waypoints_joined

    def create_waypoint_urls(self, chunks):
        waypoint_urls = []
        for chunk in chunks:
            waypoints = chunk.copy()
            origin = waypoints.pop(0)
            destination = waypoints.pop(-1)
            joined_waypoints = '|'.join(self.create_waypoint_string(waypoints))
            url = c.directions_api_base_url.format(origin=str(origin['lat']) + ',' + str(origin['lng']), destination=str(destination['lat']) + ',' + str(destination['lng']), waypoints=joined_waypoints, api_key=c.api_key)
            waypoint_urls.append((url, (origin, destination)))

        return waypoint_urls

    # TODO - Alex need to return them in order
    def split_up_waypoints(self, equidistant_markers):
        chunks = []
        i = 1
        while True:
            markers_until_end = len(equidistant_markers) - i
            if markers_until_end >= c.max_waypoints:
                chunks.append(equidistant_markers[i-1:i+c.max_waypoints])
            else:
                chunks.append(equidistant_markers[i-1:len(equidistant_markers)])
                break
            i += c.max_waypoints

        return chunks

    # TODO - Make this just handle the async responses and assign arrival times
    def get_waypoint_directions(self, equidistant_markers):
        # Set the origin of the directions as the first waypoint so it doesn't calculate a leg of 1 minute
        # Remove that marker so it's not repeated
        # origin = equidistant_markers.pop(0)
        #
        # # Get google directions using the markers as waypoints
        # waypoints_result = self.get_directions(params=params, origin=origin, waypoints=equidistant_markers)
        #
        # # Geocode destination address and extract lat/long and add it to the markers
        # equidistant_markers.append(self.googlemaps_client.geocode(params['destination'])[0]['geometry']['location'])
        #
        # # Re-add the origin to the markers
        # equidistant_markers.insert(0, origin)

        chunks = self.split_up_waypoints(equidistant_markers)
        waypoint_urls = self.create_waypoint_urls(chunks)
        async_session = AsyncHelper(waypoint_urls, None)
        results = async_session.async_all()
        # TODO - Order the results returns from async
        # TODO - Maybe pass an index along with the chunks?
        # TODO - OR Just keep track of which marker is which chunk (marker might already be in the async results)

        # Get the results in order, and then append the legs to one big list
        leg_list = []
        for chunk in chunks:
            for result in results:
                if result.result()[1][0] == chunk[0]:
                    # Then this is the result corresponding to the chunk
                    leg_list += (result.result()[0]['routes'][0]['legs'])
                    # results.remove(result)

        # Initialize total travel minutes
        total_mins = 0

        # Set arrival time of first marker to 0 minutes
        # Set address of first marker to the first waypoint's start address
        equidistant_markers[0]['arrival_time'] = 0
        equidistant_markers[0]['address'] = leg_list[0]['start_address']

        i = 1  # Index starts at 1 because the first marker has default arrival time of 0 mins

        # Iterate over legs (each waypoint-waypoint is a leg)
        for leg in leg_list:
            # Convert leg duration from seconds to minutes
            total_mins += (leg['duration']['value'] / 60)

            # Set the arrival time of the next marker to the total_mins using arrival time of current waypoint
            equidistant_markers[i]['arrival_time'] = total_mins

            # Set the address of the next marker as the end_address of the current waypoint
            equidistant_markers[i]['address'] = leg['end_address']
            i += 1

        return equidistant_markers

    @staticmethod
    def create_weather_api_urls(markers):
        url_marker_list = []
        for marker in markers:
            url_marker_tuple = (c.weather_api_base_url.format(lat=marker['lat'], lng=marker['lng']), marker)
            url_marker_list.append(url_marker_tuple)
        return url_marker_list

    def get_weather_at_markers(self, markers):
        now = datetime.datetime.now(timezone('US/Eastern'))
        url_marker_list = self.create_weather_api_urls(markers)
        async_session = AsyncHelper(url_marker_list, c.weather_api_base_headers)
        result = async_session.async_all()
        markers = []
        for response in result:
            weather_response = response.result()[0]
            marker = response.result()[1]
            utc_time_from_now = now + datetime.timedelta(minutes=marker['arrival_time'])

            for period in weather_response['properties']['periods']:
                period_start_time = parse(period['startTime']).replace(tzinfo=timezone('UTC'))
                period_end_time = parse(period['endTime']).replace(tzinfo=timezone('UTC'))

                # If the utc time at the marker is within the period, add the weather data to the marker
                if period_start_time <= utc_time_from_now < period_end_time:
                    marker['weather_data'] = period
                    markers.append(marker)
                    # Jump to next marker
                    break

