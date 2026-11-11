# Git Lost & Found

Dropped a stash? Search for a line you remember editing, preview the stash, and export it as a patch.

Requires Python 3.9+ and Git. There are no Python dependencies. Run the script from anywhere inside the repository you want to search.

```sh
/path/to/git-lost-and-found/git-lost-found search 'remembered text'
/path/to/git-lost-and-found/git-lost-found show <object-id>
/path/to/git-lost-and-found/git-lost-found show <object-id> -o recovered.patch
git apply --check recovered.patch
git apply recovered.patch
```

Use the object ID printed by `search`. To search for text beginning with a dash, put `--` before it. The search is literal and case-sensitive, and matches added and removed lines. `show` writes patch bytes to standard output by default. With `-o` it creates a new file and refuses to overwrite an existing one.

Search and preview leave your working tree and index alone. Applying a patch is a separate step. If the target has changed since you stashed, review the patch or try it in a checkout based on the stash's original commit.

## Try it in a disposable repo

Set `tool` to the absolute path to the script, then run:

```sh
tool=/path/to/git-lost-and-found/git-lost-found
demo=$(mktemp -d)
git -C "$demo" init
cd "$demo"
git -c user.name=Demo -c user.email=demo@example.org commit --allow-empty -m initial
printf 'a line worth recovering\n' > notes.txt
git -c user.name=Demo -c user.email=demo@example.org stash push -u -m demo
git stash drop
"$tool" search 'a line worth recovering'
```

## Scope

Search scans unreachable commits for the structure of a Git-created stash. It covers the stash's final tracked changes and any untracked files saved with it. The patch combines staged and unstaged changes into one result. Text search skips binary contents, but a matching stash's exported patch can include binary changes.

A dropped stash is searchable while Git still retains its objects and they are unreachable from refs and reflogs. This tool cannot recover objects Git has already pruned or edits Git never stored. Scanning a large object database can take time.

Exit codes are `0` for success, `1` for no search matches, and `2` for usage or operational errors.

## Contributing

Run the integration tests with `python3 -m unittest discover -s tests`. They use disposable repositories and require Git on your PATH.
