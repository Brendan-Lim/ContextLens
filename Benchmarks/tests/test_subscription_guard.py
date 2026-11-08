import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runners'))
import subscription_guard as guard

class SubscriptionGuardTests(unittest.TestCase):
    def snapshot(self):
        return {'ordinaryUsageAllowed':True,'rateLimits':{'planType':'plus','credits':{'hasCredits':False,'unlimited':False,'balance':'0'},'primary':{'usedPercent':29},'secondary':{'usedPercent':28},'rateLimitReachedType':None}}
    def test_included_usage_with_zero_credits_only(self):
        self.assertEqual(guard.validate(self.snapshot())['planType'],'plus')
        for key,value in [('hasCredits',True),('unlimited',True),('balance','1'),('balance',None)]:
            data=self.snapshot();data['rateLimits']['credits'][key]=value
            with self.assertRaises(ValueError):guard.validate(data)
    def test_missing_exhausted_and_credit_based_plans_fail_closed(self):
        for change in ['missing','limit','unknown','credits-plan','denied']:
            data=self.snapshot()
            if change=='missing':data['rateLimits'].pop('credits')
            elif change=='limit':data['rateLimits']['primary']['usedPercent']=80
            elif change=='unknown':data['rateLimits']['secondary']['usedPercent']=None
            elif change=='credits-plan':data['rateLimits']['planType']='enterprise_cbp_usage_based'
            else:data['ordinaryUsageAllowed']=False
            with self.assertRaises(ValueError):guard.validate(data)
    def test_command_forces_exact_model_chatgpt_standard_speed(self):
        command=guard.command()
        for required in ['gpt-6.1-sol','model_reasoning_effort="high"','forced_login_method="chatgpt"','service_tier="default"','features.fast_mode=false','--ignore-user-config','--strict-config','workspace-write']:
            self.assertIn(required,command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',command)

    def test_authorized_threshold_override_still_rejects_exhaustion_unknown_usage_and_paid_credits(self):
        data=self.snapshot();data['rateLimits']['primary']['usedPercent']=93
        with self.assertRaises(ValueError):guard.validate(data)
        self.assertEqual(guard.validate(data,max_usage_percent=100)['planType'],'plus')
        for percent in [100,101,None,float('nan')]:
            changed=copy.deepcopy(data);changed['rateLimits']['primary']['usedPercent']=percent
            with self.assertRaises(ValueError):guard.validate(changed,max_usage_percent=100)
        data['rateLimits']['credits']['balance']='1'
        with self.assertRaises(ValueError):guard.validate(data,max_usage_percent=100)
        for plan in ['plus','edu']:
            changed=self.snapshot();changed['rateLimits']['planType']=plan
            changed['rateLimits']['credits']={'hasCredits':True,'unlimited':False,'balance':None}
            with self.assertRaises(ValueError):guard.validate(changed,max_usage_percent=100)
        for threshold in [0,101,float('nan'),True]:
            with self.assertRaises(ValueError):guard.validate(self.snapshot(),max_usage_percent=threshold)

    def test_education_allocation_requires_explicit_authorization_and_known_unexhausted_usage(self):
        data=self.snapshot();data['rateLimits']['planType']='edu'
        data['rateLimits']['credits']={'hasCredits':True,'unlimited':False,'balance':None}
        with self.assertRaises(ValueError):guard.validate(data,max_usage_percent=100)
        self.assertEqual(guard.validate(data,max_usage_percent=100,allow_edu_allocation=True)['planType'],'edu')
        for change in ['denied','unknown','exhausted','missing-window','unlimited','enterprise']:
            changed=copy.deepcopy(data)
            if change=='denied':changed['ordinaryUsageAllowed']=False
            elif change=='unknown':changed['rateLimits']['primary']['usedPercent']=None
            elif change=='exhausted':changed['rateLimits']['primary']['usedPercent']=100
            elif change=='missing-window':changed['rateLimits']['secondary']=None
            elif change=='unlimited':changed['rateLimits']['credits']['unlimited']=True
            else:changed['rateLimits']['planType']='enterprise_cbp_usage_based'
            with self.assertRaises(ValueError):guard.validate(changed,max_usage_percent=100,allow_edu_allocation=True)
