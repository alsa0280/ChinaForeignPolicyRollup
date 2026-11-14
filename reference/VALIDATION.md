# Validation performed on 27 October 2026

- Twelve deterministic reference pipeline tests passed.
- The six event offline replay completed and produced a digest and database.
- The seed register contains 28 unique opportunity IDs and 55 unique source IDs. All opportunity source references resolve.
- The source catalogue includes access limitations. The 15 discovery channels have no tested live collection history.
- The final research document renders to 26 pages. The separate three column term sheet renders to two pages.
- All final document pages were visually reviewed. The latest changed pages were checked, with pixel comparisons used to confirm unchanged pages.

The tests check reference logic, not extraction quality, commercial completeness,
live source coverage, Microsoft Outlook rendering, operational reliability or
production readiness. Proposed precision and recall targets have not been measured.

Run locally with Python 3.11 or later:

```bash
python -m unittest discover -s tests -v
python pipeline.py --demo --out demo-output
```
