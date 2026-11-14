# Examples

Sample output files for documentation and UI fixtures.

- `sample-results.json` — three fictional companies in the crawler's JSON shape
- `sample-results.csv` — the same data as CSV

These files use reserved `example` domains and fictional business data. They
are safe to use in demos and screenshots. Replace them with your own output
when testing a real workflow.

Generate a real export:

```bash
curl "http://localhost:6970/results?format=csv" -o leads.csv
curl "http://localhost:6970/results?format=json" -o leads.json
```
