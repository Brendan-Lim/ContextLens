#!/usr/bin/env python3
"""Run the unchanged frozen runner with an additional Education-only stop guard.

The shared guard allows both personal included usage and explicitly permitted
Education usage. This user's authorization forbids Plus, so narrow the guard
without changing frozen tasks, commands, schedule, evaluator or runner bytes.
"""
import run_study


def require_education(snapshot):
    if snapshot.get('rateLimits',{}).get('planType') not in {'edu','edu_plus','edu_pro'}:
        raise ValueError('Education-only authorization: active allocation changed; no model call started')
    return snapshot


def main():
    original=run_study.guard.check
    def education_check(*args,**kwargs):
        return require_education(original(*args,**kwargs))
    run_study.guard.check=education_check
    run_study.main()


if __name__=='__main__':main()
