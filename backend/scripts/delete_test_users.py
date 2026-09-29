#!/usr/bin/env python3
"""One-off admin script: delete known test users from the production DB.

Most FKs in this schema have no DB-level cascade, so child rows are removed
explicitly, child-first, before deleting the user. All statements bind the
target email — the WHERE clause is part of the SQL text, so there is no way
to accidentally delete a different user by passing arguments.

Usage (run from backend/):
    python scripts/delete_test_users.py          # list-only, safe
    python scripts/delete_test_users.py --yes    # actually delete

Refuses to run against a non-Neon host by default (override with
ROLIO_ALLOW_NON_NEON=1 for local testing).
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(".env")       # backend/.env — production Neon URL
load_dotenv("../.env")    # root .env as fallback

from sqlalchemy import create_engine, text  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Test accounts, verbatim. Bound in every statement below.
# demo@rolio.com (the seeded demo account) is intentionally NOT here.
TARGET_EMAILS = [
    "featcheck0921@gmail.com",          # feature-testing signup
    "deploy-verify-1825@rolio-test.com", # deploy verification
    "live-682@rolio-test.com",           # deploy verification
    "probe2@sec.example.com",            # security-audit probe
    "probe3@sec.example.com",            # security-audit probe
]

# One statement per child table, most-dependent first. `:email` is bound
# from TARGET_EMAILS for each user in turn.
CHILD_STATEMENTS = [
    ("application_reminders",
     "DELETE FROM application_reminders WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("application_events",
     "DELETE FROM application_events WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("email_messages (null FK first)",
     "UPDATE email_messages SET matched_application_id = NULL WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("email_messages",
     "DELETE FROM email_messages WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("email_sync_logs",
     "DELETE FROM email_sync_logs WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("gmail_tokens",
     "DELETE FROM gmail_tokens WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("email_verification_tokens",
     "DELETE FROM email_verification_tokens WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("password_reset_tokens",
     "DELETE FROM password_reset_tokens WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("refresh_sessions",
     "DELETE FROM refresh_sessions WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("oauth_states",
     "DELETE FROM oauth_states WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("search_history",
     "DELETE FROM search_history WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("notifications",
     "DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("applications",
     "DELETE FROM applications WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("saved_jobs",
     "DELETE FROM saved_jobs WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    # profile children (skills/experiences/educations/projects) have no DB
    # cascade either — delete them via profile_id before the profile itself.
    ("profile children (skills etc.)",
     "DELETE FROM skills WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email))"),
    ("profile children (experiences)",
     "DELETE FROM experiences WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email))"),
    ("profile children (educations)",
     "DELETE FROM educations WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email))"),
    ("profile children (projects)",
     "DELETE FROM projects WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email))"),
    ("profiles",
     "DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("resumes",
     "DELETE FROM resumes WHERE user_id IN (SELECT id FROM users WHERE email = :email)"),
    ("users",
     "DELETE FROM users WHERE email = :email"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="actually delete")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set (run from backend/ with .env present)")
        return 2

    host = (DATABASE_URL.split("@", 1)[1].split("/", 1)[0] if "@" in DATABASE_URL else "?")
    print(f"Target host: {host}")
    if "neon.tech" not in host and os.environ.get("ROLIO_ALLOW_NON_NEON") != "1":
        print("ERROR: DATABASE_URL does not point at Neon. Set ROLIO_ALLOW_NON_NEON=1 to override.")
        return 2

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print(f"\n== {datetime.now(timezone.utc).isoformat()} ==")
        print("Users matching target emails:")
        found = []
        for email in TARGET_EMAILS:
            row = conn.execute(
                text("SELECT id, email, name, created_at FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()
            if row:
                found.append(row)
                print(f"  id={row.id}  {row.email}  name={row.name!r}  created={row.created_at}")
            else:
                print(f"  {email}: not found")

        # Count child rows for each found user.
        for row in found:
            print(f"\nChild rows for {row.email}:")
            for table, stmt in CHILD_STATEMENTS[:-1]:
                n = conn.execute(text(stmt.replace("DELETE FROM", "SELECT COUNT(*) FROM", 1)
                                          .replace("UPDATE email_messages SET matched_application_id = NULL",
                                                   "SELECT COUNT(*) FROM email_messages")),
                                 {"email": row.email}).scalar()
                print(f"  {table}: {n}")

        if not args.yes:
            print("\nList-only mode. Re-run with --yes to delete.")
            return 0

        for row in found:
            print(f"\nDeleting {row.email} ...")
            for table, stmt in CHILD_STATEMENTS:
                result = conn.execute(text(stmt), {"email": row.email})
                print(f"  {table}: {result.rowcount} row(s)")
            print(f"  done: {row.email}")

        conn.commit()

        print("\n== Verification ==")
        for email in TARGET_EMAILS:
            exists = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"), {"email": email}
            ).scalar()
            print(f"  {email}: {'STILL EXISTS' if exists else 'gone'}")

        remaining = conn.execute(text("SELECT id, email FROM users ORDER BY id")).fetchall()
        print(f"\nRemaining users: {len(remaining)}")
        for r in remaining:
            print(f"  id={r.id}  {r.email}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
