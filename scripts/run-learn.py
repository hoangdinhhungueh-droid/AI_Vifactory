#!/usr/bin/env python3
"""VF Learn Cycle — analyze audit results and generate skill enhancements
Usage:
  python scripts/run-learn.py                          # Run learn cycle for all types
  python scripts/run-learn.py --type story               # Only story audits
  python scripts/run-learn.py --days 7 --min-occurrences 2  # Last 7 days, min 2 occurrences
  python scripts/run-learn.py --queue                     # Show pending enhancement queue
"""
import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.audit.learn import run_learn_cycle, get_approval_queue, calculate_improvement

def main():
    parser = argparse.ArgumentParser(description='VF Learn Cycle — auto-enhance from audit results')
    parser.add_argument('--type', choices=['story', 'director', 'prompt'], help='Audit type filter')
    parser.add_argument('--days', type=int, default=30, help='Lookback period in days (default: 30)')
    parser.add_argument('--min-occurrences', type=int, default=3, help='Minimum occurrences for pattern (default: 3)')
    parser.add_argument('--queue', action='store_true', help='Show pending enhancement queue')
    parser.add_argument('--improvement', help='Calculate improvement: --improvement story --before 2026-08-01 --after 2026-08-15')
    parser.add_argument('--before', help='Before date (YYYY-MM-DD) for improvement calculation')
    parser.add_argument('--after', help='After date (YYYY-MM-DD) for improvement calculation')
    args = parser.parse_args()
    
    if args.queue:
        queue = get_approval_queue()
        print(f"\nPending Enhancement Proposals: {len(queue)}")
        print(f"{'='*60}")
        for item in queue:
            print(f"  ID: {item[0]}")
            print(f"  Skill: {item[1]}")
            print(f"  Type: {item[2]}")
            print(f"  Proposed: {item[4][:100]}...")
            print(f"  Confidence: {item[6]:.0%}")
            print(f"  Rationale: {item[5][:100]}...")
            print(f"  {'-'*40}")
        return
    
    if args.improvement:
        if not args.before or not args.after:
            print("Error: --improvement requires --before and --after dates")
            sys.exit(1)
        result = calculate_improvement(args.improvement, args.before, args.after)
        print(f"\nImprovement Analysis: {args.improvement}")
        print(f"  Before ({args.before}): {result['before_avg']}/10")
        print(f"  After  ({args.after}): {result['after_avg']}/10")
        print(f"  Change: {result['improvement']:+.2f} ({result['verdict']})")
        return
    
    print(f"\nRunning Learn Cycle...")
    print(f"  Type: {args.type or 'all'}")
    print(f"  Days: {args.days}")
    print(f"  Min occurrences: {args.min_occurrences}")
    print(f"{'='*60}")
    
    result = run_learn_cycle(
        audit_type=args.type,
        min_occurrences=args.min_occurrences,
        days=args.days,
    )
    
    print(f"\nResult:")
    print(f"  Total patterns found: {result['patterns']}")
    print(f"  Total proposals generated: {result['proposals']}")
    for atype, stats in result.get('by_type', {}).items():
        print(f"    {atype}: {stats['patterns']} patterns → {stats['proposals']} proposals")
    
    if result['proposals'] > 0:
        print(f"\n✅ {result['proposals']} enhancement proposals generated.")
        print(f"   High-confidence proposals sent to Telegram for approval.")
        print(f"   Run 'python scripts/run-learn.py --queue' to see pending proposals.")
    else:
        print(f"\nℹ️  No recurring patterns found in the last {args.days} days.")
        print(f"    Need more audit data for pattern recognition.")

if __name__ == '__main__':
    main()
