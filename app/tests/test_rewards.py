import unittest

from ethereum import rewards


class TestRewardsMethods(unittest.TestCase):
    BASE_REWARDS = {'user_id1': {'eth': 1, 'token': 2},
                    'user_id2': {'eth': 3, 'token': 4},
                    'user_id3': {'eth': 5, 'token': 6}}

    def test_compare_rewards_dict_copy(self):
        test_dict = self.BASE_REWARDS.copy()
        self.assertEqual(rewards.compare_rewards(self.BASE_REWARDS, test_dict), True)

    def test_compare_rewards_dict_key_order(self):
        test_dict = {'user_id3': {'token': 6, 'eth': 5},
                     'user_id1': {'eth': 1, 'token': 2},
                     'user_id2': {'token': 4, 'eth': 3},
                     }
        self.assertEqual(rewards.compare_rewards(self.BASE_REWARDS, test_dict), True)

    def test_compare_rewards_toplevel_key_mismatch(self):
        test_dict = {'user_id1': {'eth': 1, 'token': 2},
                     'user_id20': {'eth': 3, 'token': 4},
                     'user_id3': {'eth': 5, 'token': 6}}
        self.assertEqual(rewards.compare_rewards(self.BASE_REWARDS, test_dict), False)

    def test_compare_rewards_nested_key_mismatch(self):
        test_dict = {'user_id1': {'btc': 1, 'token': 2},
                     'user_id2': {'eth': 3, 'token': 4},
                     'user_id3': {'btc': 5, 'token': 6}}
        self.assertEqual(rewards.compare_rewards(self.BASE_REWARDS, test_dict), False)

    def test_compare_rewards_nested_value_mismatch(self):
        test_dict = {'user_id1': {'eth': 1, 'token': 2},
                     'user_id2': {'eth': 3, 'token': 4},
                     'user_id3': {'eth': 5, 'token': 60}}
        self.assertEqual(rewards.compare_rewards(self.BASE_REWARDS, test_dict), False)


if __name__ == '__main__':
    unittest.main()
