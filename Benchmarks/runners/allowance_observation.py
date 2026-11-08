"""Account-wide displayed quota changes are observations, never inferred per-turn charges."""
def compare(before, after):
    result={'attribution':'shared-account-unattributed','exact_per_trial_allowance':None,'windows':{}}
    for key in ['primary','secondary']:
        a=(before.get('rateLimits') or {}).get(key);b=(after.get('rateLimits') or {}).get(key)
        if not a or not b:
            result['windows'][key]={'displayed_delta_percentage_points':None,'reason':'missing-window'};continue
        if a.get('resetsAt') is None or a.get('resetsAt')!=b.get('resetsAt') or a.get('windowDurationMins')!=b.get('windowDurationMins'):
            result['windows'][key]={'displayed_delta_percentage_points':None,'reason':'window-changed-or-unknown'};continue
        x,y=a.get('usedPercent'),b.get('usedPercent')
        if type(x) not in (int,float) or type(y) not in (int,float) or not 0<=x<=y<=100:
            result['windows'][key]={'displayed_delta_percentage_points':None,'reason':'invalid-or-decreasing-reading'};continue
        result['windows'][key]={'displayed_delta_percentage_points':y-x,'reason':'displayed-change-only; zero is not proof of zero consumption'}
    return result
