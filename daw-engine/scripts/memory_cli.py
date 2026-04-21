#!/usr/bin/env python3
"""
Memory CLI for OpenDAW - Manual memory operations
Usage: python memory_cli.py [command] [options]
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from evermem_integration import OpenDAWMemoryManager


def cmd_context(args):
    """Retrieve and display session context."""
    manager = OpenDAWMemoryManager()
    manager.print_session_context(limit=args.limit)


def cmd_store_decision(args):
    """Store an architecture decision."""
    manager = OpenDAWMemoryManager()
    
    if not manager.is_available():
        print("[Error] EverMemOS not available")
        return 1
    
    files = args.files.split(',') if args.files else []
    
    success = manager.store_architecture_decision(
        decision=args.decision,
        reasoning=args.reasoning,
        files_affected=files
    )
    
    return 0 if success else 1


def cmd_store_component(args):
    """Store component integration completion."""
    manager = OpenDAWMemoryManager()
    
    if not manager.is_available():
        print("[Error] EverMemOS not available")
        return 1
    
    files = args.files.split(',') if args.files else []
    
    success = manager.store_component_integration(
        component_name=args.name,
        tests_added=args.tests,
        files_modified=files
    )
    
    return 0 if success else 1


def cmd_store_session(args):
    """Store session summary."""
    manager = OpenDAWMemoryManager()
    
    if not manager.is_available():
        print("[Error] EverMemOS not available")
        return 1
    
    date = args.date or datetime.now().strftime('%Y-%m-%d')
    achievements = args.achievements.split('|') if args.achievements else []
    
    success = manager.store_session_summary(
        session_date=date,
        components_added=args.components,
        tests_passing=args.tests,
        key_achievements=achievements
    )
    
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(
        description='OpenDAW Memory CLI - EverMemOS integration tool'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Context command
    ctx_parser = subparsers.add_parser('context', help='Show session context')
    ctx_parser.add_argument('-l', '--limit', type=int, default=5, help='Number of memories to show')
    ctx_parser.set_defaults(func=cmd_context)
    
    # Store decision command
    decision_parser = subparsers.add_parser('decision', help='Store architecture decision')
    decision_parser.add_argument('-d', '--decision', required=True, help='Decision description')
    decision_parser.add_argument('-r', '--reasoning', required=True, help='Reasoning for decision')
    decision_parser.add_argument('-f', '--files', help='Comma-separated affected files')
    decision_parser.set_defaults(func=cmd_store_decision)
    
    # Store component command
    comp_parser = subparsers.add_parser('component', help='Store component integration')
    comp_parser.add_argument('-n', '--name', required=True, help='Component name')
    comp_parser.add_argument('-t', '--tests', type=int, required=True, help='Number of tests added')
    comp_parser.add_argument('-f', '--files', help='Comma-separated modified files')
    comp_parser.set_defaults(func=cmd_store_component)
    
    # Store session command
    session_parser = subparsers.add_parser('session', help='Store session summary')
    session_parser.add_argument('-d', '--date', help='Session date (YYYY-MM-DD)')
    session_parser.add_argument('-c', '--components', type=int, required=True, help='Components added')
    session_parser.add_argument('-t', '--tests', type=int, required=True, help='Tests passing')
    session_parser.add_argument('-a', '--achievements', help='Achievements separated by |')
    session_parser.set_defaults(func=cmd_store_session)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
