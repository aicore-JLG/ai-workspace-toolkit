# Find social outliers fairly

Use public or expressly authorised data. The example CSV is synthetic.

1. Define a comparable cohort: same platform, account, format, approximate age and metric.
2. Record the full cohort, not just winners, with source/date in the owning project.
3. Choose comparable prior baseline posts, excluding the candidate. Report small samples.
4. Sort baseline values and take the median, averaging the middle two for even counts.
5. Divide the candidate metric by that median. With a zero median report undefined.
6. Inspect content and confounders: paid distribution, age, audience change and reposts.
7. Record a testable hypothesis. A high ratio is not proof of causation.

In [the synthetic CSV](../examples/research/outliers.csv), baseline views are 80, 100, 100, 110, 120. Median = 100. Candidate = 400. Ratio = 4.0. This is arithmetic, not a real account or universal threshold.

Return cohort, baseline selection, ratio, sources, observations, confounders and one testable idea. Do not copy another creator's wording or claim their results.
