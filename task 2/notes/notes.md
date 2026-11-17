# Preventing Bad Data from Reaching Users

We don’t want junk data showing up in coaches’ dashboards or in the reports they rely on. So every file that comes in has to clear two gates before it’s trusted.

First, we validate it against the exact schema we expect. That catches missing fields, wrong data types, or anything that looks malformed—right at the door. Once the data lands in the Silver layer, we run a set of configurable quality rules that flag suspicious values and inconsistencies. These rules live outside the code, so Sports Science can tweak thresholds whenever their experience grows. When a rule fires, the whole record gets flagged with the rule ID, which file it came from, which run it was part of, and exactly what the problem was. We keep the original record untouched—no silent deletion, no sneaky changes.

Only records that pass the checks or have been explicitly approved by Sports Science after review make it into the trusted analytical outputs. Everything else stays visible for investigation but is excluded from any trusted material. This way we keep the pipeline rock-solid on the technical side while giving Sports Science final say on what’s valid in their world.

# Fixing Data That’s Already Been Used

If someone spots an error after the data has already been published, we treat it seriously and keep everything traceable.

We start by finding the exact records—using source, session, run, and record references. Sports Science reviews the situation and decides on the right fix. We always keep the original raw data and the previous issue record intact.

The correction is then logged as a new version (with the old value, the new value, the reason, who approved it, and the timestamp). Once that’s done, we rebuild the Silver and Gold outputs from the corrected source, and we make sure any reports or downstream tools that depend on them get updated too.

Finally, we check that the fix really works by comparing it back to the original issue. This keeps everything auditable, stops silent changes, and gives us a clear story of what changed, why it changed, and who made the call.

# Bottom line

We never quietly overwrite or delete questionable data. We preserve the original, document the decision, and keep every correction fully traceable.