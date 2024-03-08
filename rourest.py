import argparse
import statistics as stats
import csv
from haversine import haversine
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


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


def get_location_id(str):
    split = str.split("_")
    result = '_'.join(split[1:])
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
            query_data.append({"query_id": query_id,"source_id": source_id, "destination_id": destination_id})
    return query_data

def lookup_coordinates(query_data, stops):
    for query in query_data:
        query['source_lat'] = float(stops[query['source_id']]['stop_lat'])
        query['source_lon'] = float(stops[query['source_id']]['stop_lon'])
        query['destination_lat'] = float(stops[query['destination_id']]['stop_lat'])
        query['destination_lon'] = float(stops[query['destination_id']]['stop_lon'])

def calculate_distances(query_data):
    for query in query_data:
        query['distance'] = haversine((query['source_lat'],query['source_lon']),(query['destination_lat'],query['destination_lon']))


def get_query_data(stops_file, query_file):
    query_data = read_query_file(query_file)
    stops = read_stops_file(stops_file)
    lookup_coordinates(query_data,stops)
    calculate_distances(query_data)
    return query_data


def get_response_data(response_file):
    query_id_data_idx = {}  # maps query_ids to index in the data lists
    routing_times = []  # [ms]
    interval_sizes = []  # [s]
    with open(response_file, "r") as file:
        data_idx = 0
        for line in file:
            query_id_data_idx[find_query_id(line)] = data_idx
            data_idx += 1
            routing_times.append(find_routing_time(line))
            interval_sizes.append(find_interval_end(line) - find_interval_begin(line))

    return query_id_data_idx, routing_times, interval_sizes


def get_response_stats(response_file):
    query_id_data_idx, routing_times, interval_sizes = get_response_data(response_file)

    # do statistics on routing times
    results = {}
    results["num_values"] = len(routing_times)
    results["mean"] = stats.mean(routing_times)
    results["min"] = min(routing_times)
    quantiles = stats.quantiles(routing_times)
    results["25%"] = quantiles[0]
    results["median"] = quantiles[1]
    results["75%"] = quantiles[2]
    results["max"] = max(routing_times)

    return results


def print_response_stats(response_file):
    results = get_response_stats(response_file)

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



def distance_v_interval_size(stops_file, query_file, response_file):
    query_data = get_query_data(stops_file, query_file)
    query_id_data_idx, routing_times, interval_sizes = get_response_data(response_file)

    distances = []
    interval_sizes_h_ordered = []
    for query in query_data:
        distances.append(query['distance'])
        interval_sizes_h_ordered.append(interval_sizes[query_id_data_idx[query['query_id']]] / 3600)

    fig, ax = plt.subplots(layout="constrained")
    ax.scatter(distances, interval_sizes_h_ordered, color="green", edgecolors="none", alpha=0.1)
    ax.set_title("distance v interval size (n = {})".format(len(distances)))
    plt.xlabel('distance [km]')
    plt.ylabel('interval size [h]')
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="ROUREST - Routing Response Statistics",
                                     description="Statistically evaluate routing queries and the corresponding routing responses")
    parser.add_argument("stops_file", type=str, nargs=1, help="path to the stops.txt of the GTFS timetable to lookup station coordinates")
    parser.add_argument("query_file", type=str, nargs=1,
                        help="path to the file containing the routing queries")
    parser.add_argument("response_file", type=str, nargs=1,
                        help="path to the file containing the responses to the queries")
    args = parser.parse_args()
    print_response_stats(args.response_file)
