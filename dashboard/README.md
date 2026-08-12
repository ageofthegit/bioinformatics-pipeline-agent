# Helix Visual Dashboard

This is the browser interface for the Bioinformatics Pipeline Agent. It reads
the approved dataset catalog from the local Python bridge and operates the real
interactive workflow; it does not contain a second QC implementation.

Use the project-root command documented in the main `README.md` to start both
the dashboard and its local bridge. `npm run build` and `npm test` validate the
web artifact independently.
