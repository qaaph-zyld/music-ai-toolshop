# to_be_deleted — staging area

Created by the `/clean-up` workflow on 20261004_023402.

Items here were flagged obsolete/redundant and **moved** (not deleted) so the change is reviewable and fully reversible via git.

- **Restore an item**: `git mv to_be_deleted/<path> <original/path>`
- **Roll back everything**: `git reset --hard cleanup-checkpoint-<stamp>`
- **Permanently delete**: only after human review — `rm -rf to_be_deleted/` then commit.

See `manifest.tsv` for the origin of each staged item.
