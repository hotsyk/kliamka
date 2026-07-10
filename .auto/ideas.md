# Deferred optimization ideas

- Re-evaluate bulk positional/optional Action cloning and attachment if a no-change control returns near the 13.5365us historical best. Under drift it improved creation ~8% and primary ~3% versus control but missed the best by 1.2%.
- Add permanent product tests for parser/action/registry independence, descriptor-plan invalidation, dynamic `sys.argv[0]`, and negative-number options alongside the next kept implementation change (the test set passed in experiment 31 but was auto-reverted with the losing optimization).
- Consider a completed parser-prototype clone that remaps all Actions/groups/maps in one bulk pass; only pursue if it preserves public parser extension and mutable-state independence.
