import unittest
from analisar_recuperacao import evaluate

class RecoverySensitivityTest(unittest.TestCase):
    def setup_case(self, committed=9, dlq_at=1):
        events={}
        for window in range(3):
            for i in range(committed):
                events[f'{window}-{i}']=dict(stored=True,accepted=True,response=window*10**10+2,commit=window*10**10+1)
        for i in range(3): events[f'dlq-{i}']=dict(stored=False,accepted=True,response=0,dlq_ack=dlq_at)
        observations=[dict(_time=(i+1)*10**10,database_measured=1,kafka_group_lag=0) for i in range(3)]
        return events,observations,0,0,30,1
    def test_original_keeps_terminal_as_uncommitted(self):
        self.assertFalse(evaluate(*self.setup_case(),False)['observed'])
    def test_only_exploratory_subtracts_observed_terminal_ack(self):
        self.assertTrue(evaluate(*self.setup_case(),True)['observed'])
    def test_future_ack_not_subtracted_early(self):
        self.assertFalse(evaluate(*self.setup_case(dlq_at=30*10**9+1),True)['observed'])
    def test_throughput_condition_unchanged(self):
        self.assertFalse(evaluate(*self.setup_case(committed=8),True)['observed'])
    def test_three_fresh_healthy_windows_still_required(self):
        args=list(self.setup_case()); args[1][-1]['kafka_group_lag']=3
        self.assertFalse(evaluate(*args,True)['observed'])
    def test_no_health_evidence_is_not_zero_healthy(self):
        args=list(self.setup_case()); args[1]=[]
        self.assertFalse(evaluate(*args,True)['observed'])

if __name__=='__main__': unittest.main()
