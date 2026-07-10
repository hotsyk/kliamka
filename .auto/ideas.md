# Deferred optimization ideas

- Promote the persistent `.auto/checks.sh` cache/help isolation assertions into product tests before merging/finalizing: parser/action/registry independence, descriptor-plan invalidation, idempotent lazy help, dynamic `sys.argv[0]`, and negative-number options.
- During final review, evaluate whether the private argparse cloning speedup justifies `_core.py`/`_parser.py` size; preserve the benchmarked hot paths if extracting helpers regresses performance.
