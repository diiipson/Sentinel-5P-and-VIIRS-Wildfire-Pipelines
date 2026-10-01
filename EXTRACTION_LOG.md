# Extraction Log

**Note:** the 27 original scripts and the old top-level README/
DATA_SOURCES.md/CITATION.cff referenced throughout this log have since
been removed from this repository — only the cleaned-up, separated
version (now at the repo root) is kept here. This log is retained as a
historical record of where every piece of code actually came from and
how it was validated; it's not a map to files you'll find in this repo
anymore.

This log records, for every file that is now at the repo root, exactly
which original script(s) and line ranges it was built from, what was
changed (cleanup only — no computational logic was altered unless
explicitly noted), and which parts of the published paper have **no**
corresponding code anywhere in the original 27 scripts.

Paper: Bhandari, D. (2026). *Satellite-Based Clustering of Pre-Monsoon
Wildfires and Variability of Tropospheric NO2 and CO in Nepal.*
EarthArXiv preprint, DOI: [10.31223/X5ZV2G](https://doi.org/10.31223/X5ZV2G).

Method: every one of the 27 original `.py` files was read in full
(not just skimmed) and cross-checked line-by-line against the paper's
Methods (Section 2) and Results (Section 3) text and every figure
caption. Where a file contained multiple concatenated attempts (common —
you mentioned this was written in a rush), each block was evaluated
independently to determine which one actually matches the published
method, and which were earlier iterations or dead ends.

---

## 01_tropomi_stac_download.py

- **Source:** `stacapi.py`, lines 100–222 (the "FALL BACK" resumable
  block).
- **Not used:** `stacapi.py` lines 1–98 — an earlier, non-resumable draft
  of the same download logic, left commented out in the original file.
- **Paper section:** 2.1 (Sentinel-5P TROPOMI acquisition via S5P-PAL
  STAC-API).
- **Changes:** parameterized gas/year/output dir instead of being
  hand-edited per run; bbox now from `config.py`.

## 02_viirs_gridding.py

- **Source (canonical):** `lonlatsumerror.py`, full file (222 lines) —
  run for 2024, reads grid-cell centers directly from a TROPOMI
  reference file so the VIIRS grid is guaranteed to align with TROPOMI's.
- **Also consulted / consistent with:** `regridvirsstartingpoint.py`
  (2022 run, same approach via hardcoded TROPOMI offset constants).
- **Not used — predecessor:** `finalregridalgorithm.py` lines 1–249
  ("WORKING + CF-1.10 COMPLIANT"). Same output variables and binning
  logic, but builds the grid with `np.arange(lat_min, ...)` instead of
  aligning to an actual TROPOMI grid. This is why later analysis
  scripts all read from `gridalligned_<year>_...` directories, not
  `finalregridalgorithm.py`'s own `<year>_VIIRS_daily_gridded_0.021_nc`
  output — the two are **not** interchangeable; cells don't line up.
- **Not used — incomplete:** `regrid.py` (full file) and
  `finalregridalgorithm.py`'s middle "WORKING" block (lines 252–420) —
  both omit `day_count`/`night_count`/`day_night_mode`, which Table 1
  of the paper requires.
- **Not used — inconsistent with paper:** `finalregridalgorithm.py`'s
  third block ("PREVIOUS", lines 425–587) additionally filters on
  `"algorithm QA"` bits. Paper Section 2.2 states filtering is "fire mask
  values of 8 and 9 only" — no QA-bit filtering — so this block
  implements a *different* method than what was published.
- **Not used — exploratory dead ends** (QA/fire-mask filter comparisons
  during method development, never fed into the main pipeline):
  `filtering.py`, `qafilter.py`, `qafilter1.py`, `filtermask.py`,
  `timeseparator.py`.
- **Paper section:** 2.2 (Processing and gridding the VIIRS VNP14IMG
  swath product).
- **Changes:** wrapped the "edit two paths, rerun" pattern into a loop
  over `config.STUDY_YEARS`. No binning/filtering logic changed.

## 03_hotspot_detection_clustering.py

- **Source (canonical):** `methodology1.py`, lines 389–805 — the
  **third** of three nested attempts in that file (search for
  `"before leqaving"` [sic] to find the boundary in the original). This
  is the only one using the paper's stated 90th-percentile threshold.
- **Not used — earlier thresholds:** `methodology1.py` lines 1–182 and
  184–388 both use a 95th-percentile threshold (`quantile(0.95)`),
  an earlier choice superseded by the 90th-percentile version. Also:
  `FILECHECK.py` lines 283–416 and 533–868 (all 95th percentile).
- **Also consulted:** `methodology2.py` (full file) — functionally
  equivalent 90th-percentile + CCL logic, generalized to run on the
  TROPOMI-aligned `gridalligned_<year>_...` grids and additionally
  produces the data behind Figs. 5 and 6 (see below).
- **Also consulted:** `PROVINCEAREA.py` (full file, 2024 example) — same
  detection logic with a district shapefile overlaid, used to manually
  read off which districts fall inside each cluster (feeds Table 2 and
  `DISTRICT_HOTSPOT_PERSISTENCE` in `config.py`).
- **Not used — different method entirely:** `hotspot.py` (full file)
  implements a Getis-Ord Gi* local statistic (`esda.G_Local`) with an
  adaptive Z-score threshold. This is a different, abandoned spatial
  statistics approach — the paper's published method is percentile +
  connected-component labeling, not Gi*.
- **Area equation (paper Eq. 1):** two formulas existed side by side in
  `methodology1.py`:
  - Lines ~530–559: area from the cluster's **bounding box** via the
    spherical-cap formula. This is what matches Eq. 1 exactly as written
    in the paper. Used as `compute_cluster_area_km2_bbox()`.
  - Lines ~562–630 ("SYNDER FORMULA" [sic]): a more precise **per-pixel**
    area sum (counts only actual cluster cells, not the full bounding
    box). Kept as `compute_cluster_area_km2_per_pixel()` since it's a
    legitimate alternative, but it is **not** what Eq. 1 as written
    describes.
  - **Resolved by running both against real 2021 data** (see
    "Validation" section below): the bbox formula gives 10,765.6 km²
    for 2021's largest cluster — nowhere near the paper. The per-pixel
    formula gives **2,232.2 km²**, matching paper Table 2's "2,232.20"
    almost exactly. **The per-pixel formula
    (`compute_cluster_area_km2_per_pixel`) is the one actually used for
    the published Table 2 and Eq. 1 as implemented, despite Eq. 1 as
    *written* in the paper describing the simpler bounding-box
    calculation.** This is worth fixing in a future paper revision if
    you want the text to match the code.
- **Paper sections:** 2.3.1 (percentile-based hotspot thresholding),
  2.3.2 (connected-component labeling), Eq. 1 (cluster area).
- **Changes:** wrapped in a per-year loop; both area formulas kept,
  computation logic unchanged.

## 04_cluster_trace_gas_timeseries.py

- **Source:** `FILECHECK.py`, lines 7–189. Hardcoded a single
  2024/cluster-1 bounding box and processed CO data while labeling
  every variable `NO2_*` throughout (a copy-paste artifact from an
  earlier NO2 run — the file processes whichever gas's dataset path and
  variable name were last edited in).
- **Cluster bounding boxes:** extracted verbatim from `no2costat.py`
  lines 19–40 (`clusters_by_year` dict) into
  `config.CLUSTER_BBOXES_BY_YEAR`. This is where the output of
  `03_hotspot_detection_clustering.py` was manually copied in after
  being run once per year.
- **Paper section:** data-preparation step underlying 2.4 (daily
  cluster-averaged NO2/CO) and Figs. 8/9.
- **Changes:** generalized into a loop over year × cluster × {NO2, CO}
  instead of 24 manual single-combination runs; fixed the NO2/CO
  variable-naming mismatch.

## 05_episodic_amplitude_metric_b.py (removed)

- **Source:** `no2costat.py`, lines 118–146
  (`peak_change_within_month_pct` calculation). Formula:
  `(daily_max - daily_min) / daily_min * 100` — matches paper Eq. 3
  exactly. Originally computed for CO only; the formula is gas-agnostic
  and applies identically to NO2.
- **Paper section:** 2.4.1, Metric B (intra-monthly episodic amplitude).
- **Did NOT include:** Metric A — at the time this file was written, the
  Downloads scripts with the full Metric A + B implementation hadn't
  been found yet (see "Gaps — resolved" below).
- **Status: deleted** once `07_seasonal_and_episodic_metrics.py` was
  added, since that file does everything this one did plus Metric A.
  Validated against real data before removal (see Validation section) —
  numbers matched exactly between the two, so nothing was lost by
  removing it. Kept in this log only as a record that it existed.

## 06_himalaya_zone_timeseries.py

- **Source:** `hiamalayaconc.py` (full file, written for 2024) and
  `gridoutburst.py` lines 266–389 ("TIME SERIES HIMALAYA" block, written
  for 2021) — two independent, near-duplicate implementations of the
  same daily-mean-over-mountain-zones extraction. Deduplicated into one
  shared `compute_daily_mean()` here.
- **Physiographic zones source:** both scripts load the same external
  GeoJSON — see `config.PHYSIOGRAPHIC_ZONES_URL` and `DATA_SOURCES.md`.
- **Paper section:** 3.5 (trace gas variability in the Himalayan region),
  data-preparation step for Figs. 10/11.
- **Changes:** generalized into a loop over `config.STUDY_YEARS`.

## figures/fig01_physiographic_zones.py

- **Source:** `gridoutburst.py`, lines 604–773 (the final, reprojected
  version with a proper legend). An earlier simple draft (lines
  548–563, `gdf.plot(column='DESCRIPTIO', ...)` with no custom colors)
  is superseded. The original file also had this exact ~170-line block
  duplicated twice in a row (lines 567–709 and 711–773 are near-identical
  copies) — only one copy is kept here.
- **Paper figure:** Fig. 1.

## figures/fig02_no2_co_fire_overlay.py

- **Source:** `fig2.py`, full file (372 lines) minus its final section
  (lines 325–373, a "normal distribution of daily fire count by year"
  histogram — unrelated exploratory analysis, not a paper figure, not
  extracted).
- **Not used — earlier draft:** `methodology.py` lines 150–301, an
  earlier version of the NO2 overlay without the PowerNorm contrast
  stretching or fire/NO2 grid-mismatch handling.
- **Paper figures:** Fig. 2 (NO2 overlay) and Fig. S1 (CO overlay).

## figures/fig03_fig04_cluster_maps.py

- **Source:** `methodology1.py`, lines 390–529 ("SAME COLOR" section).
  This exact code (with its hardcoded save path
  `S:\viirs\pictures\Clusters\2021\new_cluster{i}.png`) produced the
  `Cluster1.png` / `Cluster2.png` sample images already committed in
  `Picture samples/` in the parent repo.
- **Not used — earlier attempts:** `methodology1.py` lines 1–388 use
  `tab20` without a fixed `BoundaryNorm`, so cluster-ID-to-color mapping
  isn't stable between the full map and the zoomed panels — fixed in
  the version used here.
- **Paper figures:** Fig. 3 (full cluster map) and Fig. 4 (zoomed top-3
  panels).

## figures/fig05_daily_fire_count_timeseries.py

- **Source:** `methodology2.py`, lines 30–80 (whole-year accumulation)
  and 183–196 (the plot itself, labeled "whole year plot" in-file).
- **Paper figure:** Fig. 5.

## figures/fig06_cluster_spatial_extent_maps.py

- **Source:** `methodology2.py`, lines 145–170.
- **Paper figure:** Fig. 6.

## figures/fig07_district_persistence_map.py

- **Source:** `nepalshape.py`, lines 116–218 (final version with
  horizontal colorbar + district-name labels). An earlier vertical-
  colorbar draft (lines 49–114) is superseded.
- **District persistence table:** hand-compiled (not computed by any
  script) — extracted verbatim into `config.DISTRICT_HOTSPOT_PERSISTENCE`.
- **Paper figure:** Fig. 7.

## figures/fig08_fig09_no2_co_vs_fire_panels.py

- **Source:** `FILECHECK.py`, lines 7–189, generalized across all
  year × cluster combinations using `04_cluster_trace_gas_timeseries.py`.
  The committed `Picture samples/Figure_8.jpg` matches this exact
  12-panel layout.
- **Paper figures:** Fig. 8 (NO2) and Fig. 9 (CO).

## figures/fig10_himalaya_timeseries.py

- **Source:** `gridoutburst.py`, lines 394–498 (plotting + unit
  conversion, built on the shared extraction in
  `06_himalaya_zone_timeseries.py`).
- **Paper figure:** Fig. 10.

---

## Files added after the "Gaps" below were resolved

These were not found anywhere in `S:\viirs\Filtering` or `S:\viirs\` —
they were located directly on the machine at
`C:\Users\ACER\Downloads\`, outside both of those locations. See "Gaps —
resolved" below for how they were found.

## 07_seasonal_and_episodic_metrics.py

- **Source:** `C:\Users\ACER\Downloads\no2_stat_both_metrics.py` and
  `C:\Users\ACER\Downloads\co_stat_both_metrics.py` (sections 1–7 of
  each — settings, cluster bboxes, daily extraction, Jan–Feb baseline,
  monthly Metric A + Metric B, peak rows).
- **Supersedes (and replaced):** `05_episodic_amplitude_metric_b.py`,
  which only had Metric B (from `no2costat.py` inside this repo, which
  never computed Metric A). Deleted once this file was validated as
  doing everything the old one did, plus Metric A.
- **Paper section:** 2.4.1, both Metric A (Eq. 2) and Metric B (Eq. 3),
  for both gases.

## 08_monthly_and_lagged_correlation.py

- **Source:** `C:\Users\ACER\Downloads\spearman_correlation_with_lag.py`,
  sections 9a/9b/9c — the same logic also appears duplicated inside
  `no2_stat_both_metrics.py` and `co_stat_both_metrics.py`.
- **Paper sections:** 2.4.2 (monthly Spearman) and 2.4.3 (lagged daily
  Spearman). This is the source of the paper's headline correlation
  numbers.
- **Validated against real 4-year NO2 data** (see Validation section):
  reproduces ρ=0.820 for fire-vs-Metric-A and the lag-0/1/2/3 profile
  (0.661/0.678/0.658/0.616) **exactly matching the paper's published
  numbers to 3 decimal places.**
- **Methodological note found during validation:** sections 9b (raw gas
  value) and 9c (gas anomaly relative to baseline) produce **identical**
  lag results. This isn't a bug — Spearman rank correlation is invariant
  to subtracting a per-group constant, and the baseline is exactly that
  (one constant per cluster-year). This holds in the original scripts
  too, since the computation structure is unchanged — worth knowing if
  you reference 9b and 9c as if they could differ.

## 09_himalaya_correlation_analysis.py

- **Source:** `C:\Users\ACER\Downloads\himalaya_analysis_improved.py`,
  sections 6–9 (Himalaya baseline, Metric A/B, monthly Spearman
  Terai-vs-Himalaya, partial Spearman controlling for month, and the
  daily same-day "transport" analysis pooling anomalies across the 3
  Terai clusters).
- **Paper section:** 3.5 (Himalaya trace gas variability), the
  Terai-Himalaya correlation numbers (pooled ρ=0.585, per-year
  2021–2024: 0.788/0.740/0.401/0.623).

## figures/fig11_himalaya_metrics_heatmap.py

- **Source:** `C:\Users\ACER\Downloads\himalaya_analysis_improved.py`,
  "ORIGINAL PLOT 2" section — the only script found anywhere (inside or
  outside this repo) that produces this figure.
- **Paper figure:** Fig. 11.

## figures/figS_correlation_plots.py

- **Source:** `no2_stat_both_metrics.py` / `co_stat_both_metrics.py`
  sections 11–14, and `himalaya_analysis_improved.py` "NEW PLOT 2" /
  "NEW PLOT 3" sections. Consolidated into one file instead of being
  duplicated per gas.
- **Not included:** "NEW PLOT 1" (partial-Spearman raw-vs-partial bar
  chart) — the numbers are computed by
  `09_himalaya_correlation_analysis.py`'s `partial_spearman()`, just not
  plotted; add a bar chart if you need that exact figure back.
- **Paper figures:** Fig. S2/S4 (monthly scatter + lag bar), Fig. S3/S5
  (per-year lagged scatter), Fig. S6 (Terai-Himalaya scatter), Fig. S7
  (yearly transport ρ bar chart).

## Also found, but NOT used: fig2_viirs_fire_metrics.py / v2 / v3

Found alongside the files above in `C:\Users\ACER\Downloads\`. These
implement a **different** Fig. 2 design: a single day (2021-04-01),
5-panel grid of the raw fire metrics with **no TROPOMI NO2 background
overlay** and no 7-day averaging. This does not match the paper's actual
Fig. 2 caption ("Seven-day mean... tropospheric NO2... overlaid with
VIIRS-derived fire variables"). These look like an earlier/alternate
design for Fig. 2 that was not the one ultimately published — the
version already extracted as `figures/fig02_no2_co_fire_overlay.py`
(from `fig2.py` inside this repo) is the one that matches the paper.

---

## Validation

Every stage below was executed against your real data on disk (never
against the committed repo — all outputs went to a scratch folder,
nothing under `S:\viirs\` was modified) to confirm the extracted code
actually runs and produces correct results, not just that it parses.

- **`02_viirs_gridding.py`**: ran `grid_one_year()` on the real
  `VNP14IMG_002-20251219_081958` raw folder (121 granules, April 2021),
  aligned to a real TROPOMI NO2 file. Produced 30 daily gridded NetCDFs
  with plausible fire counts (e.g. 3,658 fires on 2021-04-03, consistent
  with the known early-April 2021 fire peak). **Works.**
- **`03_hotspot_detection_clustering.py`**: ran `detect_hotspot_clusters()`
  on the real `gridalligned_2021_VIIRS_daily_gridded_0.021_nc` directory
  with the real Nepal boundary shapefile. Result: top-3 cluster sizes
  **425 / 260 / 254 cells**, bounding boxes lat 27.938–28.839°N /
  27.169–27.587°N / 28.795–29.279°N — **matches paper Table 2's 2021 row
  (425/260/254 cells) exactly**, and matches the bounding boxes
  hardcoded in `config.CLUSTER_BBOXES_BY_YEAR` exactly. **Works, and
  reproduces the paper's own published numbers.**
- **`04_cluster_trace_gas_timeseries.py`**: ran `extract_cluster_timeseries()`
  on real 2021 NO2 data and the real 2021 cluster-1 bounding box — 327
  valid daily rows extracted. **Works.**
- **`05_episodic_amplitude_metric_b.py`** (since deleted, see entry
  above): ran `monthly_episodic_amplitude()` on the output of the
  above — produced March/April/May 2021 episodic amplitudes
  (254%/227%/877%), same order of magnitude as the paper's reported
  range for this metric. **Worked** — and these exact numbers were
  reproduced again by `07_seasonal_and_episodic_metrics.py` below,
  which is why removing this file was safe.
- **`06_himalaya_zone_timeseries.py`**: fetched the real physiographic
  zones GeoJSON (2 mountain zones found, as expected) and ran
  `compute_daily_mean()` on 5 real NO2 files. **Works.**
- **`figures/fig01_physiographic_zones.py`**,
  **`figures/fig07_district_persistence_map.py`**,
  **`figures/fig03_fig04_cluster_maps.py`**: all ran end-to-end against
  real data with `savefig` redirected to a scratch folder. The
  `fig03/fig04` output for 2021 cluster 1 visually matches the committed
  `Picture samples/Cluster1.png` (same shape, same colors, same lat/lon
  extent). **Work.**
- **`07_seasonal_and_episodic_metrics.py`**: ran `compute_both_metrics()`
  on real 2021 cluster-1 NO2 data. Episodic amplitudes matched
  `05_episodic_amplitude_metric_b.py`'s numbers exactly (254%/227%/877%);
  seasonal enhancement came out 82%/160%/22% for Mar/Apr/May, consistent
  with the paper's reported NO2 Metric A range. **Works.**
- **`08_monthly_and_lagged_correlation.py`**: ran `main("NO2")` across
  **all 4 years × 3 clusters of real data** (the first full-scale,
  not-spot-checked run in this validation pass). Result: **ρ=0.820 for
  fire-vs-Metric-A, and lag-0/1/2/3 mean ρ = 0.661/0.678/0.658/0.616 —
  matches the paper's published Section 3.3 numbers to 3 decimal
  places.** This is the strongest validation in this whole log: the
  extracted code reproduces the paper's own headline statistics from
  raw data. **Works.**

**Not executed against real data** (no real raw input available in this
environment, or requires outputs chained from a full 4-year run):
`01_tropomi_stac_download.py` (would require live network calls against
S5P-PAL and actually downloading multi-GB files — reviewed by inspection
only, logic unchanged from the working `stacapi.py`), `figures/fig02`,
`fig05`, `fig06`, `fig08_fig09`, `fig10` (these loop over all 4 years;
spot-checking the single-year/single-cluster logic they're built from
was judged sufficient rather than running a multi-hour, multi-GB full
pipeline pass).

**Related discovery that led to resolving the gaps below:** `S:\viirs\`
(the parent of this repo) contains a `himalaya_analysis\` folder and
several top-level CSVs (`NO2_lagged_daily_correlation_2021_2024.csv`,
`CO_monthly_enhancement_baseline_2021_2024.csv`,
`himalaya_lagged_correlation_profile.png`, etc.) whose names correspond
exactly to the "Gaps" originally listed below. These are real outputs of
that analysis, but an exhaustive search across all of `S:\viirs\` found
no source file that produced them. A follow-up whole-machine search
found the actual source scripts at `C:\Users\ACER\Downloads\` — see
"Gaps — resolved" below.

## Files consulted but with no corresponding pipeline file

- `boxplot_fire.py` — seasonal boxplots + skewness of daily fire count,
  read from a pre-aggregated `fire_daily_2021_2024.csv` that **no
  script in this repo produces**. Not described anywhere in the paper
  (no boxplot figure, no skewness statistic) — exploratory analysis,
  likely unused in the final manuscript.
- `firecountstat.py` — annual/monthly fire-count summary statistics
  (total, mean, median, active days, % of annual total per month).
  Matches the narrative numbers in Results 3.1 ("April accounted for
  ~62% of annual detections") but isn't itself a named figure or
  equation — not extracted as a pipeline stage, but worth knowing it's
  where those percentages come from if you need to regenerate them.
- `combinetropomiviirs.py` — single-day prototype for interpolating
  TROPOMI onto the VIIRS grid (nearest-neighbor). This is the pattern
  that was presumably batch-run to produce the `merged_<year>/*.nc`
  files consumed by `fig2.py` and others, but the batch version itself
  wasn't found in any of the 27 files — only this single-day manual
  version.
- `dailyanalysis.py`, `monthlygrid.py`, `FILECHECK.py` lines 1–4 and
  420–530 — quick-look/diagnostic scripts, not tied to a specific
  figure or equation.

## Gaps — resolved

The original version of this section listed five pieces of analysis
(Metric A, monthly Spearman correlation, lagged daily Spearman
correlation, the Himalaya-Terai correlation, and Fig. 11) that were
confirmed absent from all 27 scripts in `S:\viirs\Filtering` — verified
by reading every file in full and by grepping all of them for
`spearman`, `pearsonr`, `scipy.stats`, `baseline`, `corrcoef` (the only
hit was an unrelated `from scipy.stats import mode` import used for
day/night-mode calculation in `finalregridalgorithm.py`).

**All five were subsequently found** — not in `S:\viirs\Filtering` or
anywhere under `S:\viirs\`, but directly on the local machine at
`C:\Users\ACER\Downloads\`:

- `no2_stat_both_metrics.py`, `co_stat_both_metrics.py` — Metric A and B
  (gap #1)
- `spearman_correlation_with_lag.py` — monthly + lagged Spearman
  correlation (gaps #2, #3)
- `himalaya_analysis_improved.py` — Himalaya-Terai correlation and the
  Fig. 11 heatmap (gaps #4, #5)

They were located by searching the whole machine (`C:` and `S:`, the
only two drives accessible) for every `.py`/`.ipynb` file, then manually
filtering out Python standard library, Conda/Miniconda environments,
and VS Code extension noise to find genuinely user-authored files.

These are now extracted into `07_seasonal_and_episodic_metrics.py`,
`08_monthly_and_lagged_correlation.py`,
`09_himalaya_correlation_analysis.py`,
`figures/fig11_himalaya_metrics_heatmap.py`, and
`figures/figS_correlation_plots.py` — see those sections above for
provenance, and the Validation section below for the real-data test
that reproduced the paper's own ρ=0.820 and lag-profile numbers exactly.

**Nothing remains unaccounted for from the original "Gaps" list.**
