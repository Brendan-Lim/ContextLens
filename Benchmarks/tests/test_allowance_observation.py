from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import allowance_observation as quota

class AllowanceObservationTests(unittest.TestCase):
    def snapshot(self, used, reset=100):
        return {'rateLimits':{'primary':{'usedPercent':used,'resetsAt':reset,'windowDurationMins':300}}}
    def test_flat_display_is_not_zero_cost(self):
        observation=quota.compare(self.snapshot(20),self.snapshot(20))
        self.assertEqual(observation['windows']['primary']['displayed_delta_percentage_points'],0)
        self.assertIsNone(observation['exact_per_trial_allowance'])
        self.assertEqual(observation['attribution'],'shared-account-unattributed')
    def test_reset_or_decrease_is_not_a_saving(self):
        for after in [self.snapshot(1,200),self.snapshot(19),self.snapshot(None)]:
            self.assertIsNone(quota.compare(self.snapshot(20),after)['windows']['primary']['displayed_delta_percentage_points'])
    def test_increase_is_only_displayed_percentage_points(self):
        self.assertEqual(quota.compare(self.snapshot(20),self.snapshot(22))['windows']['primary']['displayed_delta_percentage_points'],2)
