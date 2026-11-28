# Member 2 — Implementation guide

## Start in VS Code
Open Terminal > New Terminal. Run `git status`, `git fetch origin`, `git branch -a`. Do not discard any changes. If you do not have the repository: `git clone https://github.com/M2W-E/Multi-Branch-Campus-Pharmacy-Inventory.git`, then `cd Multi-Branch-Campus-Pharmacy-Inventory`, then `code .`. Use your own Git identity (`git config user.name "Your Name"` and `git config user.email "Your GitHub email"`). If the repository is already cloned, do not clone again.

## Branch
If your branch exists locally, run `git switch member2-database-persistence`. If it exists only remotely, run `git switch --track origin/member2-database-persistence`. If it does not exist, ask the leader to confirm that `origin/integration` contains the prerequisites, then run `git switch -c member2-database-persistence origin/integration`. For an existing branch, ask the leader to help merge the approved integration baseline into it, if needed. Do not merge unreviewed branches.
## Your steps
1. Keep your existing database.py, repositories.py, schema.sql, init_db.py and tests. Copy price_storage.py and tests/test_price_storage.py from this package into the same paths in your project.
2. In repositories.py add `from price_storage import sqlite_price` near the imports. In MedicineRepository, in **each** of add_medicine, save_medicine and update_medicine, add `unit_price = sqlite_price(unit_price)` immediately before `with _managed_connection(...)`. Change these three price type annotations to `Decimal | int | float | str` and import `Decimal` from decimal. No other changes required for this starter fix. This policy rejects values that cannot round-trip through the current NUMERIC storage; it does not promise exact arbitrary precision. Ask the leader to approve the policy.
3. Run `python init_db.py --database member2_demo.sqlite3` and `python -B -m unittest discover -s tests -p "test_price_storage.py" -v` then `python -B -m unittest discover -s tests -p "test_member2_persistence.py" -v`. Add a test inserting Decimal('12.50') through the actual repository and recovering it. If an existing test expects a raw SQLite error for invalid prices, report it and update the test only to match the agreed new validation.
4. Existing seed code can reset seeded prescription status or stock when rerun. Use `--seed` only on a fresh disposable demo database until the leader fixes that. Do not commit SQLite files.
5. Write docs/database_design.md in your own words describing the six tables, foreign keys, pricing boundary and test results.
6. `git add price_storage.py repositories.py tests/test_price_storage.py`; `git commit -m "fix(database): validate Decimal persistence"`. Stage your actual updated tests and docs separately, commit them, and push.

## Upload
Run `git status`, check that only your files are committed, then `git push -u origin member2-database-persistence`. If prompted, sign in to your GitHub account in the browser. Never share a password or token. Run `git log --oneline -5` and send the leader your branch URL, actual test output and any blockers. Do not merge into main. If a command fails, stop and share the exact error.

These are starter implementation files, not independently verified against the entire live repository. Read, test and understand them, and document any AI assistance.
