**Technical Notes: Processing Performance and Duplicate Handling**

**Efficient processing of large nested files**

Processing massive nested files efficiently is one of those classic engineering challenges that can either make or break your project timeline. Each match file lands as a roughly 400 MB JSON document packed with about 140,000 frames, where every frame contains rich ball and player tracking data. Trying to load the entire document into memory first would be a disaster — it would spike RAM usage and slow everything down without any real benefit. Instead, I’d lean on a streaming JSON parser to handle the nested structure frame by frame, pulling out manageable batches of frames and their associated tracking observations as I go.

I’d avoid hammering every single record one-by-one. Batch processing combined with bulk writes is the way to keep I/O costs low and database overhead minimal. The nested JSON would be gently flattened into separate frame-level records and player-observation records, while still keeping the original relationships and source identifiers crystal clear. Before anything hits the database, I’d run schema validation, standardise data types, and run through a solid set of data-quality checks. Once the transformed data is ready, it gets published.

If independent match files are in the queue, I’d process them concurrently but with controlled concurrency levels — just enough to stay under our resource limits and avoid choking the system.

For the analytical side, the biggest player-observation table would be built around real-world access patterns. I’d cluster or sort by period, player, and frame (where the database allows) so queries fly. Any player-period metrics that get hit constantly would be pre-aggregated instead of forcing the system to crunch millions of raw observations every single time.

**Duplicate file delivery**

On the duplicate side, making ingestion fully idempotent is non-negotiable if we want to keep things clean and safe. The moment a file lands, I’d generate its SHA-256 content hash and check it against the exact combination of provider, source match ID, and content hash already stored in the `INGESTION_DELIVERY` table.

If the exact same match file with the same hash has already been processed, I’d log it as a duplicate and completely skip it — no reloading, no extra work, no risk of duplicates creeping in. That’s simple, reliable, and exactly what we need for production robustness.

If the match ID is the same but the content hash is different, I’d treat it as a potentially corrected delivery and spin up a fresh `MATCH_VERSION` instead of blindly overwriting anything. This new version gets the full validation treatment before it ever becomes the current one. Only if the processing succeeds does it promote to the active version. If anything goes wrong during processing, the previous valid version stays safely in place — no data loss, no surprises.

On top of all that, unique constraints on both the delivery identity and the fact-table keys act as an extra safety net. They make sure we can’t accidentally ingest the same thing twice, even under heavy load or edge cases. This whole approach has been my steady thinking throughout the project — it keeps things fast, scalable, and bulletproof against the kind of duplicate headaches that can derail everything when you’re handling real tracking data.