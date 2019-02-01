from src.modules.WhetherAlgorithm import WhetherAlgorithm
from src.modules.WeatherApiHelper import WeatherApiHelper
import src.constants as c


def whether_handler(params):
    # Instantiate the algorithm class
    whether_algorithm = WhetherAlgorithm()

    # Get directions from url params
    directions_result = whether_algorithm.get_directions(params)

    # Extract each polyline from each leg of the directions
    # Decode each one of these polylines to produce the points
    all_polyline_points = whether_algorithm.extract_polylines(directions_result)

    # Get equidistant markers
    equidistant_markers = whether_algorithm.get_equidistant_markers_from_polyline_points(all_polyline_points, c.marker_distance)

    # Use the GoogleMaps Waypoints API to get the times at arrived at each marker
    # As well as a new set of "directions results" to supply the user
    waypoints_results, equidistant_markers_markers_with_time = whether_algorithm.get_waypoint_directions(params, equidistant_markers)

    # Get the weather data at each marker
    equidistant_markers_with_weather = WeatherApiHelper().get_weather_at_markers(equidistant_markers)

    # Format Whether result
    result = {
        'directions': waypoints_results[0],
        'equidistant_markers': equidistant_markers_with_weather
    }
    return result


