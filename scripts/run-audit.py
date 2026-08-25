#!/usr/bin/env python3
"""VF Audit Runner — run audit from command line
Usage:
  python scripts/run-audit.py --episode en-enron-ep006 --type story --stage S2 --story-file /tmp/vf/story.txt
  python scripts/run-audit.py --episode en-enron-ep006 --type director --stage S2.5 --scenes-file /tmp/vf/scenes.json
  python scripts/run-audit.py --episode en-enron-ep006 --type prompt --stage S2.5 --scenes-file /tmp/vf/prompts.json
  python scripts/run-audit.py --episode en-enron-ep006 --type story --stage S2 --story-text "Once upon a time..."
"""
import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv("/root/secrets/.env")

from app.audit.engine import run_audit

def main():
    parser = argparse.ArgumentParser(description='VF Audit Runner — automated quality audit')
    parser.add_argument('--episode', required=True, help='Episode ID (e.g. en-enron-ep006)')
    parser.add_argument('--type', required=True, choices=['story', 'director', 'prompt', 'image'], help='Audit type')
    parser.add_argument('--stage', required=True, help='Pipeline stage (S2, S2.5, S5, S9)')
    parser.add_argument('--story-file', help='Path to story text file (for story audit)')
    parser.add_argument('--scenes-file', help='Path to scenes JSON file (for director/prompt audit)')
    parser.add_argument('--story-text', help='Story text directly (for story audit)')
    args = parser.parse_args()
    
    # Load content
    content = {}
    if args.story_file:
        with open(args.story_file) as f:
            content['story_text'] = f.read()
    elif args.story_text:
        content['story_text'] = args.story_text
    elif args.scenes_file:
        with open(args.scenes_file) as f:
            data = json.load(f)
        content['scenes'] = data if isinstance(data, list) else data.get('scenes', data.get('prompts', []))
    
    # Run audit
    result = run_audit(args.episode, args.type, args.stage, content)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"  AUDIT RESULT: {args.type.upper()}")
    print(f"  Episode: {args.episode}")
    print(f"  Stage: {args.stage}")
    print(f"  Score: {result['score']}/10")
    print(f"  Verdict: {result['verdict']}")
    print(f"  Elapsed: {result.get('elapsed_s', 0)}s")
    print(f"{'='*60}")
    print(f"\nAxis Scores:")
    for axis, score in sorted(result['axis_scores'].items(), key=lambda x: x[1]):
        bar = '█' * int(score) + '░' * (10 - int(score))
        print(f"  {axis:20s} {score:4.1f} {bar}")
    
    if result['issues']:
        print(f"\nIssues ({len(result['issues'])}):")
        for issue in result['issues']:
            severity = issue.get('severity', 'medium').upper()
            print(f"  [{severity}] {issue.get('axis', '?')}: {issue.get('message', '')[:80]}")
    
    if result['recommendations']:
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for rec in result['recommendations']:
            print(f"  [{rec.get('priority', 'medium')}] {rec.get('skill', '')}: {rec.get('update', '')[:80]}")
    
    print(f"\nAudit ID: {result.get('audit_id', 'N/A')}")
    print(f"LLM Used: {result.get('llm_used', 'rule_only')}")
    
    # Exit code based on verdict
    if result['verdict'] == 'APPROVED':
        sys.exit(0)
    elif result['verdict'] == 'REVIEW':
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == '__main__':
    main()
