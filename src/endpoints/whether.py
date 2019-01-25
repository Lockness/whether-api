from src.modules.WhetherAlgorithm import WhetherAlgorithm


def whether_handler(params):
    whether_algorithm = WhetherAlgorithm()
    # Get directions from url params
    directions_result = whether_algorithm.get_directions(params)

    # Extract polyline
    polyline = directions_result[0]['overview_polyline']['points']

    # Get equidistant markers
    equidistant_markers = whether_algorithm.get_equidistant_markers_from_polyline(polyline)

    # Get updated directions based on markers
    # Get updated markers based on waypoint times
    waypoints_results, equidistant_markers_markers_with_time = whether_algorithm.get_waypoint_directions(params, equidistant_markers)

    # Format whether result
    result = {
        'directions': waypoints_results[0],
        'equidistant_markers': equidistant_markers_markers_with_time
    }

    return result


