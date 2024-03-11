import argparse
import statistics as stats
import csv
from haversine import haversine
import matplotlib.pyplot as plt

umlaut_replacements = {"\\u00DF": "ß", "\\u00E4": "ä", "\\u00F6": "ö", "\\u00FC": "ü", "\\u00C4": "Ä", "\\u00D6": "Ö",
                       "\\u00DC": "Ü"}


def find_between(line, begin_str, end_str):
    start = line.find(begin_str) + len(begin_str)
    end = line.find(end_str, start)
    return line[start:end]


def rfind_between(line, begin_str, end_str):
    start = line.rfind(begin_str) + len(begin_str)
    end = line.find(end_str, start)
    return line[start:end]


def find_query_id(line):
    value_str = rfind_between(line, '"id":', "}")
    return int(value_str.strip())


def find_routing_time(line):
    value_str = find_between(line, '"routing_time_ms","value":', "}")
    return int(value_str.strip())


def find_interval_begin(line):
    value_str = find_between(line, '"interval_begin":', ",")
    return int(value_str.strip())


def find_interval_end(line):
    value_str = find_between(line, '"interval_end":', ",")
    return int(value_str.strip())


def replace_umlaut_codes(string):
    for code, umlaut in umlaut_replacements.items():
        string = string.replace(code, umlaut)
    return string


def get_location_id(string):
    split = string.split("_")
    result = '_'.join(split[1:])  #
    result = replace_umlaut_codes(result)
    return result


def find_source_id(line):
    value_str = find_between(line, '"start": {"station": {"id": "', '"')
    value_str = get_location_id(value_str)
    return value_str


def find_destination_id(line):
    value_str = find_between(line, '"destination": {"id": "', '"')
    value_str = get_location_id(value_str)
    return value_str


def read_stops_file(stops_file):
    stops = {}
    with open(stops_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            stops[row['stop_id']] = row
    return stops


def read_query_file(query_file):
    query_data = []
    with open(query_file, "r") as file:
        for line in file:
            query_id = find_query_id(line)
            source_id = find_source_id(line)
            destination_id = find_destination_id(line)
            query_data.append({"query_id": query_id, "source_id": source_id, "destination_id": destination_id})
    return query_data


def lookup_coordinates(query_data, stops):
    for query in query_data:
        query['source_lat'] = float(stops[query['source_id']]['stop_lat'])
        query['source_lon'] = float(stops[query['source_id']]['stop_lon'])
        query['destination_lat'] = float(stops[query['destination_id']]['stop_lat'])
        query['destination_lon'] = float(stops[query['destination_id']]['stop_lon'])


def calculate_distances(query_data):
    for query in query_data:
        query['distance'] = haversine((query['source_lat'], query['source_lon']),
                                      (query['destination_lat'], query['destination_lon']))


def get_query_data(stops_file, query_file):
    query_data = read_query_file(query_file)
    stops = read_stops_file(stops_file)
    lookup_coordinates(query_data, stops)
    calculate_distances(query_data)
    return query_data


def get_response_data(response_file):
    routing_times = {}  # [ms]
    interval_sizes = {}  # [s]
    with open(response_file, "r") as file:
        for line in file:
            query_id = find_query_id(line)
            routing_times[query_id] = find_routing_time(line)
            interval_sizes[query_id] = (find_interval_end(line) - find_interval_begin(line)) / 3600

    return routing_times, interval_sizes


def get_response_stats(routing_times):
    # do statistics on routing times
    results = {}
    results["num_values"] = len(routing_times)
    results["mean"] = stats.mean(routing_times.values())
    results["min"] = min(routing_times.values())
    quantiles = stats.quantiles(routing_times.values())
    results["25%"] = quantiles[0]
    results["median"] = quantiles[1]
    results["75%"] = quantiles[2]
    results["max"] = max(routing_times.values())

    return results


def print_response_stats(routing_times):
    results = get_response_stats(routing_times)

    # print results
    print("--- Routing Time Statistics ---")
    print("#values: " + str(results["num_values"]))
    print("   mean: " + str(round(results["mean"])) + " ms")
    print("    min: " + str(results["min"]) + " ms")
    print("    25%: " + str(round(results["25%"])) + " ms")
    print(" median: " + str(round(results["median"])) + " ms")
    print("    75%: " + str(round(results["75%"])) + " ms")
    print("    max: " + str(results["max"]) + " ms")
    print("-------------------------------")


def plot_distance_v_routing_time(query_data, routing_times):
    distances = []
    routing_times_ordered = []

    for query in query_data:
        max_dist = 3000
        # skip distance outliers due to false coordinates in stops.txt
        if query['distance'] > max_dist:
            print('query distance {} > {}: discarding {}'.format(query['distance'], max_dist, query))
            continue

        distances.append(query['distance'])
        routing_times_ordered.append(routing_times[query['query_id']])

    fig, ax = plt.subplots(layout="constrained")
    ax.scatter(distances, routing_times_ordered, color="green", edgecolors="none", alpha=0.1)
    ax.set_title("distance v routing time (n = {})".format(len(distances)))
    plt.xlabel('distance [km]')
    plt.ylabel('routing time [ms]')
    plt.show()


def plot_distance_v_interval_size(query_data, interval_sizes):
    distances = []
    interval_sizes_ordered = []

    for query in query_data:
        max_dist = 3000
        # skip distance outliers due to false coordinates in stops.txt
        if query['distance'] > max_dist:
            print('query distance {} > {}: discarding {}'.format(query['distance'], max_dist, query))
            continue

        distances.append(query['distance'])
        interval_sizes_ordered.append(interval_sizes[query['query_id']])

    fig, ax = plt.subplots(layout="constrained")
    ax.scatter(distances, interval_sizes_ordered, color="green", edgecolors="none", alpha=0.1)
    ax.set_title("distance v interval size (n = {})".format(len(distances)))
    plt.xlabel('distance [km]')
    plt.ylabel('interval size [h]')
    plt.show()


def plot_interval_size_v_routing_time(interval_sizes, routing_times):
    fig, ax = plt.subplots(layout="constrained")
    ax.scatter(interval_sizes.values(), routing_times.values(), color="green", edgecolors="none", alpha=0.1)
    ax.set_title("interval size v routing time (n = {})".format(len(interval_sizes)))
    plt.xlabel('interval size [h]')
    plt.ylabel('routing time [ms]')
    plt.show()


def read_data(stops_file, query_file, response_file):
    query_data = get_query_data(stops_file, query_file)
    routing_times, interval_sizes = get_response_data(response_file)
    return query_data, routing_times, interval_sizes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="ROUREST - Routing Response Statistics",
                                     description="Statistically evaluate routing queries and the corresponding routing responses")
    parser.add_argument("stops_file", type=str, nargs=1,
                        help="path to the stops.txt of the GTFS timetable to lookup station coordinates")
    parser.add_argument("query_file", type=str, nargs=1,
                        help="path to the file containing the routing queries")
    parser.add_argument("response_file", type=str, nargs=1,
                        help="path to the file containing the responses to the queries")
    args = parser.parse_args()
    print("input paths:")
    print("stops_file = {}".format(args.stops_file[0]))
    print("query_file = {}".format(args.query_file[0]))
    print("response_file = {}".format(args.response_file[0]))

    query_data, routing_times, interval_sizes = read_data(args.stops_file[0], args.query_file[0], args.response_file[0])

    print_response_stats(routing_times)
    plot_interval_size_v_routing_time(interval_sizes, routing_times)
    plot_distance_v_interval_size(query_data, interval_sizes)
    plot_distance_v_routing_time(query_data, routing_times)
