# Assumptions

- The supplied sample files are representative of the data we can expect from the tracking provider.
- Each match and session has an identifier that can be used to track its data.
- A player may have multiple device assignments during a session, and these should not automatically be treated as duplicates.
- Sports Science is responsible for defining and reviewing domain-specific quality thresholds.
- Suspicious data should be flagged and retained rather than automatically deleted.
- The assessment is a proof of concept, so local Parquet storage and CSV-based review are sufficient.