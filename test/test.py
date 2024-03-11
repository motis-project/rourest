import unittest
import rourest
from statistics import mean
from statistics import quantiles

expected_query_id_data_idx = {1: 9, 2: 1, 5: 5, 6: 3, 8: 0, 12: 7, 14: 6, 15: 2, 16: 4, 20: 8}
expected_routing_times = [360, 418, 784, 825, 889, 995, 1601, 1662, 999, 1850]
expected_interval_sizes = [8.016666666666667, 4.016666666666667, 2.0166666666666666, 4.016666666666667,
                           6.016666666666667, 4.016666666666667, 4.016666666666667, 2.0166666666666666,
                           4.016666666666667, 4.016666666666667]
expected_query_id_distances = {1: 298.5018236099454, 2: 214.1739625460696, 5: 244.96749861463252, 6: 53.46407769736269,
                               8: 181.13311046805126, 12: 14.62848431110017, 14: 209.65397955705987,
                               15: 398.63930912257604, 16: 156.84004368848682, 20: 450.6600236062579}


class TestCase(unittest.TestCase):
    def test_get_response_data(self):
        query_id_data_idx, routing_times, interval_sizes = rourest.get_response_data("./responses.txt")
        self.assertEqual(expected_query_id_data_idx, query_id_data_idx)
        self.assertEqual(expected_routing_times, routing_times)
        self.assertEqual(expected_interval_sizes, interval_sizes)

    def test_get_stats(self):
        results = rourest.get_response_stats("./responses.txt")
        self.assertEqual(10, results["num_values"])
        self.assertEqual(mean(expected_routing_times), results["mean"])
        self.assertEqual(min(expected_routing_times), results["min"])
        exp_quantiles = quantiles(expected_routing_times)
        self.assertEqual(exp_quantiles[0], results["25%"])
        self.assertEqual(exp_quantiles[1], results["median"])
        self.assertEqual(exp_quantiles[2], results["75%"])
        self.assertEqual(max(expected_routing_times), results["max"])

    def test_print_stats(self):
        rourest.print_response_stats("./responses.txt")

    def test_read_stops_file(self):
        rourest.read_stops_file("./stops.txt")

    def test_get_query_data(self):
        query_data = rourest.get_query_data("./stops.txt", "./queries.txt")
        for query in query_data:
            self.assertEqual(expected_query_id_distances[query["query_id"]], query["distance"])

    def test_distance_v_interval_size(self):
        rourest.distance_v_interval_size('stops.txt', 'queries.txt', 'responses.txt')


if __name__ == '__main__':
    unittest.main()
