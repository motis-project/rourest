import argparse
import statistics as stats
import numpy as np
import csv
from haversine import haversine
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

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
    val_list = list(routing_times.values())

    results = {}
    results["num_values"] = len(val_list)
    results["mean"] = stats.mean(val_list)
    results["min"] = min(val_list)
    results["25%"] = np.percentile(val_list, 25)
    results["median"] = np.percentile(val_list, 50)
    results["75%"] = np.percentile(val_list, 75)
    results["95%"] = np.percentile(val_list, 95)
    results["99%"] = np.percentile(val_list, 99)
    results["99.9%"] = np.quantile(val_list, 0.999)
    results["max"] = max(val_list)

    return results


def print_response_stats(routing_times):
    results = get_response_stats(routing_times)

    # print results
    print("--- Routing Time Statistics ---")
    print("  #values: " + str(results["num_values"]))
    print("      min: " + str(results["min"]) + " ms")
    print("      25%: " + str(round(results["25%"])) + " ms")
    print("   median: " + str(round(results["median"])) + " ms")
    print("     mean: " + str(round(results["mean"])) + " ms")
    print("      75%: " + str(round(results["75%"])) + " ms")
    print("      95%: " + str(round(results["95%"])) + " ms")
    print("      99%: " + str(round(results["99%"])) + " ms")
    print("    99.9%: " + str(round(results["99.9%"])) + " ms")
    print("      max: " + str(results["max"]) + " ms")
    print("-------------------------------")


def plot_routing_times(routing_times, name):
    pos = [1]
    data = [list(routing_times.values())]
    fig, axs = plt.subplots(1,2,layout='constrained')

    violin_parts = axs[0].violinplot(data, pos, showextrema=True, showmedians=True)

    # adjust colors
    violin_parts["cmedians"].set_color("black")
    violin_parts["cmins"].set_color("black")
    violin_parts["cmaxes"].set_color("black")
    violin_parts["cbars"].set_color("black")
    for part in violin_parts["bodies"]:
        part.set_alpha(1)
    violin_parts["bodies"][0].set_color("blue")

    axs[0].set_yscale('linear')
    axs[0].set_title("linear y-axis".format(len(routing_times)))
    axs[0].set_ylabel("Query response time [ms]")

    plt.subplot(1, 2, 2)
    violin_parts = axs[1].violinplot(data, pos, showextrema=True, showmedians=True)

    # adjust colors
    violin_parts["cmedians"].set_color("black")
    violin_parts["cmins"].set_color("black")
    violin_parts["cmaxes"].set_color("black")
    violin_parts["cbars"].set_color("black")
    for part in violin_parts["bodies"]:
        part.set_alpha(1)
    violin_parts["bodies"][0].set_color("blue")

    axs[1].set_yscale('log')
    axs[1].set_title("logarithmic y-axis".format(len(routing_times)))
    axs[1].set_ylabel("Query response time [ms]")

    fig.suptitle("Query response times (n = {})".format(len(routing_times)))
    plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    plt.grid(axis="y")

    plt.show()


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
    ax.set_yscale('log')
    ax.scatter(distances, routing_times_ordered, color="green", edgecolors="none", alpha=0.1)
    ax.set_title("distance v routing time (n = {})".format(len(distances)))
    plt.xlabel('distance [km]')
    plt.ylabel('routing time [ms]')
    plt.grid(True)
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
    plt.grid(True)
    plt.show()


def plot_interval_size_v_routing_time(interval_sizes, routing_times):
    fig, ax = plt.subplots(layout="constrained")
    ax.set_yscale('log')
    ax.scatter(interval_sizes.values(), routing_times.values(), color="green", edgecolors="none", alpha=0.1)
    ax.set_title("interval size v routing time (n = {})".format(len(interval_sizes)))
    plt.xlabel('interval size [h]')
    plt.ylabel('routing time [ms]')
    plt.grid(True)
    plt.show()


def plot_compare_routing_times(routing_times, names):
    pos = [1,2]
    data = [list(routing_times[0].values()), list(routing_times[1].values())]
    fig, ax = plt.subplots(layout='constrained')
    violin_parts = ax.violinplot(data, pos, showextrema=True, showmedians=True)

    # adjust colors
    violin_parts["cmedians"].set_color("black")
    violin_parts["cmins"].set_color("black")
    violin_parts["cmaxes"].set_color("black")
    violin_parts["cbars"].set_color("black")
    for part in violin_parts["bodies"]:
        part.set_alpha(1)
    violin_parts["bodies"][0].set_color("blue")
    violin_parts["bodies"][1].set_color("green")

    # legend
    blue_patch = mpatches.Patch(color='blue', label=names[0])
    green_patch = mpatches.Patch(color='green', label=names[1])
    ax.legend(handles=[blue_patch, green_patch], loc='upper center')

    ax.set_yscale('log')
    ax.set_title("Comparison of query response times (n = {})".format(len(routing_times[0])))
    ax.set_ylabel("Query response time [ms]")
    plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    plt.grid(axis="y")
    plt.show()


def stat_dict_2_list(stat_dict):
    stat_list = []
    stat_list.append(stat_dict['min'])
    stat_list.append(stat_dict['25%'])
    stat_list.append(stat_dict['median'])
    stat_list.append(stat_dict['mean'])
    stat_list.append(stat_dict['75%'])
    stat_list.append(stat_dict['95%'])
    stat_list.append(stat_dict['99%'])
    stat_list.append(stat_dict['99.9%'])
    stat_list.append(stat_dict['max'])
    return stat_list


def plot_compare_routing_time_stats(routing_times, names):
    pos = [1,2,3,4,5,6,7,8,9]
    labels = ["min", "25%", "median", "mean", "75%", "95%", "99%", "99.9%", "max"]
    file1_stats = stat_dict_2_list(get_response_stats(routing_times[0]))
    file2_stats = stat_dict_2_list(get_response_stats(routing_times[1]))
    fig, ax = plt.subplots(layout='constrained')

    ax.plot(pos, file1_stats, label=names[0])
    ax.plot(pos, file2_stats, label=names[1])

    ax.legend(loc="upper left", ncols=1)

    ax.set_yscale('log')
    ax.set_title("Comparison of query response time statistics (n = {})".format(len(routing_times[0])))
    ax.set_xlabel("Stats")
    ax.set_ylabel("Query response time [ms]")
    plt.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax.set_xticks(pos, labels=labels)
    plt.grid(True)
    plt.show()

def read_data(stops_file, query_file, response_file):
    query_data = get_query_data(stops_file, query_file)
    routing_times, interval_sizes = get_response_data(response_file)
    return query_data, routing_times, interval_sizes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="ROUREST - Routing Response Statistics",
                                     description="Statistically evaluate routing queries and the corresponding routing responses")
    parser.add_argument("-s", "--stops_file", type=str, required=True,
                        help="path to the stops.txt of the GTFS timetable to lookup station coordinates")
    parser.add_argument("-q", "--query_file", type=str, required=True,
                        help="path to the file containing the routing queries")
    parser.add_argument("-r", "--response_file", type=str, required=True,
                        help="path to the file containing the responses to the queries")
    parser.add_argument("-c", "--compare_file", type=str, required=False, help="path the response file to compare")
    args = parser.parse_args()

    print("input paths:")
    print("stops_file = {}".format(args.stops_file))
    print("query_file = {}".format(args.query_file))
    query_data = get_query_data(args.stops_file, args.query_file)
    routing_times = []
    interval_sizes = []
    names = []

    print("response_file = {}".format(args.response_file))
    rt_dict, is_dict = get_response_data(args.response_file)
    routing_times.append(rt_dict)
    interval_sizes.append(is_dict)
    names.append(os.path.basename(args.response_file))

    if args.compare_file:
        print("compare_file = {}".format(args.compare_file))
        rt_dict, is_dict = get_response_data(args.compare_file)
        routing_times.append(rt_dict)
        interval_sizes.append(is_dict)
        names.append(os.path.basename(args.compare_file))

    if args.compare_file is None:
        print_response_stats(routing_times[0])
        plot_routing_times(routing_times[0], os.path.basename(args.response_file))
        plot_interval_size_v_routing_time(interval_sizes[0], routing_times[0])
        plot_distance_v_interval_size(query_data, interval_sizes[0])
        plot_distance_v_routing_time(query_data, routing_times[0])
    else:
        print("Stats for response file {}".format(names[0]))
        print_response_stats(routing_times[0])
        print("Stats for response file {}".format(names[1]))
        print_response_stats(routing_times[1])
        plot_compare_routing_times(routing_times, names)
        plot_compare_routing_time_stats(routing_times, names)
