import math
from datetime import datetime
import googlemaps
import numpy as np
from src.modules.GoogleClient import GoogleClient


class WhetherAlgorithm:
    def __init__(self):
        self.googlemaps_client = GoogleClient().client

    def get_directions(self, params, waypoints=None, origin=None):
        now = datetime.now()
        if waypoints is not None:
            result = self.googlemaps_client.directions(origin, params['destination'], mode='driving',
                                                       departure_time=now, waypoints=waypoints,
                                                       optimize_waypoints=True)
        else:
            result = self.googlemaps_client.directions(params['origin'], params['destination'], mode='driving',
                                                       departure_time=now)
        return result

    @staticmethod
    def extract_polylines(directions_result):
        all_points = []
        for step in directions_result[0]['legs'][0]['steps']:
            polyline_points = step['polyline']['points']
            decoded_points = googlemaps.convert.decode_polyline(polyline_points)
            if len(all_points) == 0:
                all_points = decoded_points
            else:
                all_points.extend(decoded_points[1:])

        return all_points

    def get_equidistant_markers_from_polyline_points(self, points, distance):
        """
        Given set of points, returns set of points that are evenly spaced along
        said points

        :param points: list of dict coords of lat/long
        :param distance: distance between points, in km
        :return: list of dict of coords lat/long
        """
        # from dict to array
        points = np.array([list(d.values()) for d in points])

        # array of sequential points
        sequ_points = np.empty((len(points) - 1, 4))

        sequ_points[:, :2] = points[:-1]
        sequ_points[:, 2:] = points[1:]

        # distances between points, and remainders
        distances = np.apply_along_axis(WhetherAlgorithm.haversine, 1, sequ_points)
        mods = (distances.cumsum() % distance)

        # get steps: start at distance, with step of distance until end
        steps = np.arange(distance, distances.sum(), distance)

        # locations where steps insert
        inserts = np.searchsorted(distances.cumsum(), steps) - 1

        # look for duplicates
        uns, idxs, cnts = np.unique(inserts, return_index=True, return_counts=True)

        # append remainders to tweeners in order to np apply
        tweeners = sequ_points[uns + 1]
        remainders = (distance - mods[uns])

        # look for and process duplicates
        m_dup = (cnts > 1).nonzero()[0]

        # TODO: the points generated here don't look optimal, figure it out
        # however with the detailed polylines it rarely gets called unless distance is very small
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
        dict_even_points = [{'lat': lat, 'lng': lng} for lat, lng in even_points]

        # add first and last points
        dict_even_points += [{'lat': lat, 'lng': lng} for lat, lng in [points[0], points[-1]]]

        return dict_even_points

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

    def get_waypoint_directions(self, params, equidistant_markers):
        # Set the origin of the directions as the first waypoint so it doesn't calculate a leg of 1 minute
        # Remove that marker so it's not repeated
        origin = equidistant_markers.pop(0)

        # Get google directions using the markers as waypoints
        waypoints_result = self.get_directions(params=params, origin=origin, waypoints=equidistant_markers)

        # Geocode destination address and extract lat/long and add it to the markers
        equidistant_markers.append(self.googlemaps_client.geocode(params['destination'])[0]['geometry']['location'])

        # Re-add the origin to the markers
        equidistant_markers.insert(0, origin)

        # Initialize total travel minutes
        total_mins = 0

        # Set arrival time of first marker to 0 minutes
        equidistant_markers[0]['arrival_time'] = 0

        i = 1  # Index starts at 1 because the first marker has default arrival time of 0 mins

        # Iterate over legs (each waypoint-waypoint is a leg)
        for leg in waypoints_result[0]['legs']:
            # Convert leg duration from seconds to minutes
            total_mins += (leg['duration']['value'] / 60)

            # Set the arrival time to the total_mins
            equidistant_markers[i]['arrival_time'] = total_mins
            i += 1

        return waypoints_result, equidistant_markers
