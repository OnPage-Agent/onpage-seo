# Contributing

Thanks for helping. Three rules keep this skill trustworthy:

1. **Every check cites a source.** Add it to `RULES` in `scripts/audit.py` with a link to Google's
   or Bing's documentation. If it's an editorial convention, mark it `True` in the last field
   (shown as "best practice").
2. **No dependencies.** The script stays standard-library Python 3.10+, so it runs anywhere Claude
   Code does.
3. **No invented numbers.** The skill never estimates traffic, rankings or search volumes.

Before opening a pull request:

```bash
python3 -m unittest discover -s tests -v
```

Add a page to the test site in `tests/test_audit.py` that triggers your check, and one that
shouldn't. Framework and platform guides live in `references/`; keep them to the official way of
doing things in each tool.

The README images are built from real output: see `docs/src/` (`build_previews.py`, then
`render.sh`, which needs Google Chrome).
