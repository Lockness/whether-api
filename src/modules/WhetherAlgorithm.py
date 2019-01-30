import googlemaps
from datetime import datetime
import math
import geopy.distance
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

    def get_equidistant_markers_from_polyline_points(self, points):
        # Get markers
        next_marker_at = 0
        markers = []
        while True:
            next_point = self.iterative_move_along_path(points, next_marker_at)

            if next_point is not None:
                markers.append({'lat': next_point[0], 'lng': next_point[1]})
                next_marker_at += 80000  # About 50 miles
            else:
                break
        print(markers)
        return markers

    @staticmethod
    def move_towards(point1, point2, distance):
        # Convert degrees to radians
        lat1 = math.radians(point1[0])
        lon1 = math.radians(point1[1])
        lat2 = math.radians(point2[0])
        d_lon = math.radians(point2[1] - point1[1])

        # Find the bearing from point1 to point2
        bearing = math.atan2(math.sin(d_lon) * math.cos(lat2),
                             math.cos(lat1) * math.sin(lat2) -
                             math.sin(lat1) * math.cos(lat2) *
                             math.cos(d_lon))

        # Earth's radius
        ang_dist = distance / 6371000.0

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

        return [math.degrees(lat2), math.degrees(lon2)]

    def iterative_move_along_path(self, points, distance, index=0):
        while index < len(points) - 1:
            # There is still at least one point further from this point
            # Turn points into tuples for geopy format
            # point1_tuple = (points[index]['latitude'], points[index]['longitude'])
            # point2_tuple = (points[index + 1]['latitude'], points[index + 1]['longitude'])
            point1_tuple = (points[index]['lat'], points[index]['lng'])
            point2_tuple = (points[index + 1]['lat'], points[index + 1]['lng'])

            # Use geodesic method to get distance between points in meters
            distance_to_next_point = self.haversine(point1_tuple, point2_tuple)

            if distance <= distance_to_next_point:
                # Distance_to_next_point is within this point and the next
                # Return the destination point with moveTowards()
                return self.move_towards(point1_tuple, point2_tuple, distance)

            else:
                # The destination is further from the next point
                # Subtract distance_to_next_point from distance and continue recursively
                distance -= distance_to_next_point
                index += 1

        # There are no further points, the distance exceeds the length of the full path.
        # Return None
        return None

    @staticmethod
    def haversine(point1_tuple, point2_tuple):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        lat1, lon1 = point1_tuple
        lat2, lon2 = point2_tuple
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        # Radius of earth in kilometers is 6371
        m = 6371000 * c
        return m

    # def move_along_path(self, points, distance, index=0):
    #     if index < len(points) - 1:
    #         # There is still at least one point further from this point
    #         # Turn points into tuples for geopy format
    #         # point1_tuple = (points[index]['latitude'], points[index]['longitude'])
    #         # point2_tuple = (points[index + 1]['latitude'], points[index + 1]['longitude'])
    #         point1_tuple = (points[index]['lat'], points[index]['lng'])
    #         point2_tuple = (points[index + 1]['lat'], points[index + 1]['lng'])
    #
    #         # Use geodesic method to get distance between points in meters
    #         distance_to_next_point = geopy.distance.geodesic(point1_tuple, point2_tuple).m
    #
    #         if distance <= distance_to_next_point:
    #             # Distance_to_next_point is within this point and the next
    #             # Return the destination point with moveTowards()
    #             return self.move_towards(point1_tuple, point2_tuple, distance)
    #
    #         else:
    #             # The destination is further from the next point
    #             # Subtract distance_to_next_point from distance and continue recursively
    #             return self.move_along_path(points, distance - distance_to_next_point, index + 1)
    #
    #     else:
    #         # There are no further points, the distance exceeds the length of the full path.
    #         # Return None
    #         return None

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

    # NOT CURRENTLY IN USE BUT MIGHT NEED IT AT SOME POINT
    # def get_snapped_points(self, points):
    #     PAGINATION_OVERLAP = 10
    #     PAGE_SIZE_LIMIT = 100
    #     all_snapped_points = []
    #     offset = 0
    #     while offset < len(points):
    #         if offset > 0:
    #             offset -= PAGINATION_OVERLAP
    #
    #         lowerBound = offset;
    #         upperBound = min(offset + PAGE_SIZE_LIMIT, len(points))
    #         page = points[lowerBound:upperBound]
    #         page_snapped_points = self.googlemaps_client.snap_to_roads(page, interpolate=True)
    #         passedOverlap = False
    #         for point in page_snapped_points:
    #             if passedOverlap or (offset == 0) or (point['originalIndex'] >= PAGINATION_OVERLAP - 1):
    #                 passedOverlap = True
    #                 all_snapped_points.append(point['location'])
    #
    #         offset = upperBound
    #
    #     return all_snapped_points
