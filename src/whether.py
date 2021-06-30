import constants as c
from WhetherAlgorithm import WhetherAlgorithm


def whether_handler(params):
    # Instantiate the algorithm class
    whether_algorithm = WhetherAlgorithm()

    # Get directions from url params
    directions_result = whether_algorithm.get_directions(params)

    # Extract each polyline from each leg of the directions
    # Decode each one of these polylines to produce the points
    all_polyline_points = whether_algorithm.extract_polylines(directions_result)

    # Get equidistant markers
    marker_distance = params.get('marker_distance', c.marker_distance)
    equidistant_markers = whether_algorithm.get_equidistant_markers_from_polyline_points(all_polyline_points, int(marker_distance))

    # Use the GoogleMaps Waypoints API to get the times at arrived at each marker
    # As well as a new set of "directions results" to supply the user
    waypoints_results = whether_algorithm.get_waypoint_directions(equidistant_markers)

    # Get the weather data at each marker
    whether_algorithm.get_weather_at_markers(equidistant_markers)

    # Format Whether result
    result = {
        'polyline': directions_result[0]['overview_polyline']['points'],
        'equidistant_markers': waypoints_results
    }
    return result


