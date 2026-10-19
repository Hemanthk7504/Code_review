"""CLI entrypoint for autonomous PR review and revision branch creation.
Used by GitHub Actions workflow and terminal executions.
"""
import argparse
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .engine.pipeline import process_pull_request


async def async_main():
    parser = argparse.ArgumentParser(description="CodeSentinel PR Review Runner")
    parser.add_argument("--repo", required=True, help="GitHub repository owner/repo (e.g. Hemanthk7504/Code_review)")
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    parser.add_argument("--token", required=False, default=None, help="GitHub access token (or via GITHUB_TOKEN env)")
    parser.add_argument("--no-create-pr", action="store_true", help="Only review and comment; do not open a revision PR")
    args = parser.parse_args()

    token = args.token or os.getenv("GITHUB_TOKEN")
    create_revision_pr = not args.no_create_pr

    print(f"🚀 Starting CodeSentinel review on PR #{args.pr} in {args.repo}...")
    try:
        result = await process_pull_request(args.repo, args.pr, token, create_revision_pr=create_revision_pr)
        print("✅ Review completed successfully!")
        print(f"Files analyzed: {result.get('files', 0)}")
        summary = result.get("summary", {})
        print(f"Total findings: {summary.get('total_findings', 0)} (Verified: {summary.get('verified', 0)})")
        print(f"Revisions accepted: {result.get('revisions_accepted', 0)}")

        revision_pr = result.get("revision_pr")
        if revision_pr:
            print(f"🎉 New revision PR opened with corrected code: {revision_pr}")
        elif summary.get('verified', 0) == 0:
            print("✨ No verified security or bug defects detected in this PR.")
        else:
            print("ℹ️ Review comment posted to original PR.")
        return 0
    except Exception as err:
        print(f"❌ Error during PR review execution: {err}", file=sys.stderr)
        return 1


def main():
    code = asyncio.run(async_main())
    sys.exit(code)


if __name__ == "__main__":
    main()
