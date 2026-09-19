# SUMO-DTLBA Experimental Evaluation Package

## 1. Overview

This package contains the simulation scripts, reference cryptographic
benchmark code, mobility traces, CSV outputs, and figures used to
evaluate the proposed **DTLBA (Digital Twin-Assisted Lattice-Based
Authentication)** framework for vehicular communications.

The package is organized around three complementary experiments:

1.  **Digital-twin mobility prediction:** evaluates next-RSU prediction
    using SUMO/TraCI mobility as ground truth.
2.  **Component-wise ablation:** compares Full DTLBA with variants in
    which DT prediction or batch verification is disabled, and evaluates
    batch scalability and wrong-prediction behavior.
3.  **End-to-end vehicle-density evaluation:** combines
    measured/reference DTLBA processing with a packet-level
    communication model to study authentication latency under 50, 100,
    200, 400, and 800-vehicle conditions.

The files are intended to support reproducibility of the manuscript's
performance evaluation. The package distinguishes measured/reference
processing time from simulated wireless communication latency and should
not be interpreted as a physical-radio or production-grade cryptographic
implementation.

------------------------------------------------------------------------

## 2. Package Structure

``` text
SUMO_DTLBA/
|
|-- DTLBA_dt_prediction_mobility_v2.py
|-- DTLBA_dt_prediction_results.py
|-- DTLBA_module_lattice_batch_v4.py
|-- DTLBA_end_to_end_density_v1.py
|
|-- hyd.net.xml
|-- routes.rou.xml
|-- routes.rou.alt.xml
|-- trips.trips.xml
|-- hyd.osm
|
|-- dt_prediction_events_v2.csv
|-- dt_handover_events_v2.csv
|-- dt_step_metrics_v2.csv
|-- dt_rsu_locations_v2.csv
|-- dt_summary_v2.csv
|
|-- batch_scalability_raw_v3.csv
|-- batch_scalability_summary_v3.csv
|-- batch_rB_sweep_raw_v4.csv
|-- batch_rB_sweep_summary_v4.csv
|-- batch_rB_crossover_v4.csv
|-- batch_rB_sweep_summary_v4.txt
|-- invalid_batch_raw_v3.csv
|-- invalid_batch_summary_v3.csv
|-- signature_communication_v3.csv
|-- DTLBA_v3_summary.txt
|
|-- e2e_density_results/
|   |-- e2e_density_overall.csv
|   |-- e2e_density_repetitions.csv
|   |-- e2e_density_communication.csv
|   |-- e2e_density_summary.txt
|   |-- fig_e2e_latency_vs_density.png
|   |-- fig_e2e_components_vs_density.png
|   |-- fig_e2e_throughput_vs_density.png
|   `-- fig_e2e_packet_loss_vs_density.png
|
|-- fig_ablation_latency.png
|-- fig_batch_verification.png
|-- fig_communication_overhead.png
|
`-- additional legacy/comparison scripts and figures
```

The archive also contains earlier comparison, plotting, and SUMO
configuration files. The four scripts beginning with `DTLBA_` and their
associated CSV outputs are the primary files for reproducing the revised
DT/mobility, ablation, and end-to-end experiments.

------------------------------------------------------------------------

## 3. Software Requirements

### 3.1 Python

Python 3 is required. The current scripts use standard Python modules
together with NumPy and Matplotlib.

Recommended packages:

``` bash
pip install numpy matplotlib
```

### 3.2 SUMO

The DT mobility experiment requires **Simulation of Urban MObility
(SUMO)** and its TraCI Python interface.

Install SUMO and define the `SUMO_HOME` environment variable so that the
script can locate the SUMO `tools` directory.

Example on Windows:

``` bat
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
```

or, depending on the installation:

``` bat
set SUMO_HOME=C:\Program Files\Eclipse\Sumo
```

On Linux, use the path corresponding to the local SUMO installation.

The principal mobility script expects the following files in its working
directory:

``` text
hyd.net.xml
routes.rou.xml
```

### 3.3 Reference cryptographic implementation

`DTLBA_module_lattice_batch_v4.py` implements the operation structure
used for the revised DTLBA MLWR performance study in Python/NumPy. It is
a reference benchmarking implementation rather than an audited
production cryptographic library.

For manuscript claims based on a C++/NTL/OpenSSL implementation, retain
the corresponding C++ source, compiler/version, library versions, build
flags, and raw timing logs with the reproducibility package. The Python
benchmark in this archive must not by itself be described as evidence of
an OpenSSL/NTL implementation.

------------------------------------------------------------------------

## 4. Experiment 1: DT-Assisted Next-RSU Prediction

### 4.1 Purpose

`DTLBA_dt_prediction_mobility_v2.py` evaluates whether the digital-twin
mobility component can correctly predict the RSU that a vehicle will
enter next.

SUMO/TraCI provides the vehicle trajectory ground truth. The predictor:

-   assigns vehicles to the nearest RSU using Voronoi-like serving
    regions;
-   maintains at most one active prediction for each vehicle;
-   extrapolates vehicle motion over a fixed prediction horizon;
-   generates a prediction only when the extrapolated position indicates
    a transition to another RSU;
-   resolves the prediction when the actual RSU transition occurs;
-   records correct, wrong, expired, vehicle-left, and simulation-end
    outcomes separately.

This separation is important because **prediction accuracy is calculated
only over resolved predictions**, whereas the **prediction resolution
rate** reports how many predictions could actually be matched to a
subsequent transition.

### 4.2 Main configuration

The principal configuration in the script is:

``` text
SUMO step length              = 1.0 s
Simulation duration           = 3600 s
Random seed                   = 42
Number of RSUs                = 8
Prediction horizon            = 10 s
Prediction cooldown           = 5 s
Prediction timeout            = 60 s
Minimum prediction speed      = 1.0 m/s
Minimum future-distance gain  = 5.0 m
```

These values should remain fixed when reproducing the reported results
unless the purpose is explicitly to conduct a sensitivity analysis.

### 4.3 Running the mobility experiment

From the `SUMO_DTLBA` directory:

``` bash
python DTLBA_dt_prediction_mobility_v2.py
```

The script generates:

-   `dt_prediction_events_v2.csv` -- event-level prediction outcomes;
-   `dt_handover_events_v2.csv` -- observed RSU handovers;
-   `dt_step_metrics_v2.csv` -- time-step mobility/load statistics;
-   `dt_rsu_locations_v2.csv` -- RSU coordinates used by the experiment;
-   `dt_summary_v2.csv` -- overall prediction metrics.

### 4.4 Reported mobility results

The included output reports:

  Metric                                   Result
  --------------------------------- -------------
  Total predictions                         1,502
  Resolved predictions                        959
  Correct predictions                         956
  Wrong predictions                             3
  Prediction resolution rate             63.8482%
  Top-1 next-RSU accuracy                99.6872%
  False-prefetch rate                     0.3128%
  Observed RSU handovers                      960
  Handovers with prior prediction             959
  Handover-prediction coverage           99.8958%
  Mean inference time                 0.006531 ms
  Mean prediction lead time             10.0292 s

The principal inference is that the predictor correctly identified the
next RSU for 956 of the 959 resolved predictions, while providing
approximately 10 s of mean lead time for proactive preparation. Accuracy
and resolution rate must be reported separately; unresolved/expired
predictions must not be counted as correct predictions.

------------------------------------------------------------------------

## 5. Experiment 2: Revised Module-Lattice Authentication and Batch Verification

### 5.1 Purpose

`DTLBA_module_lattice_batch_v4.py` evaluates the revised DTLBA
authentication and randomized batch-verification implementation. The
experiment is intentionally separated from the SUMO mobility/network
evaluation so that cryptographic microbenchmark timings are not mixed
with packet-level communication latency.

The script evaluates:

-   individual exact module-lattice verification;
-   randomized aggregate verification over batch sizes
    `1, 2, 5, 10, 25, 50, 100, 200, 300, 500`;
-   repetition counts `r_B = 1, 2, 4, 6`;
-   the measured crossover batch size `B_min`;
-   recursive invalid-request localization for batch sizes
    `10, 25, 50, 100`;
-   invalid-request ratios `0%, 5%, 10%, 20%, 30%`;
-   reference authentication-field communication sizes.

All experimental points use 30 repetitions.

### 5.2 Cryptographic parameter separation

The implementation separates the existing MLWR credential/session-key
layer from the module-lattice authentication layer.

#### MLWR credential/session-key layer

  Parameter                 Value
  ----------------------- -------
  Polynomial degree `N`       512
  Module dimension `k`          3
  Modulus `q`               12289
  Rounding modulus `p`        256
  Noise parameter               3

#### Experimental authentication layer

  Parameter                        Value
  -------------------------- -----------
  Polynomial degree `N_s`            256
  Modulus `q_s`                8,380,417
  Matrix rows `k_s`                    4
  Matrix columns `l_s`                 5
  Secret bound `eta_s`                 2
  Challenge weight `tau_s`            39
  `gamma_1`                       131072
  Response bound `B_z`            130994

The public authentication matrix is `A_sig in R_(q_s)^(k_s x l_s)`.
These authentication values form an **experimental DTLBA prototype
configuration**. The complete tuple must not be represented as an ML-DSA
parameter set or as establishing an ML-DSA/NIST security category.

### 5.3 Authentication relation

For request `i`, the experimental implementation uses a short secret
`s_i` and public authentication value

``` text
t_i = A_sig s_i mod q_s.
```

For message `M_i`, the signer forms

``` text
w_i = A_sig y_i mod q_s
c_i = H_c(M_i || w_i)
z_i = y_i + c_i s_i
sigma_i = (w_i, z_i, c_i).
```

After timestamp, response-bound, and challenge-binding checks,
individual verification evaluates the exact relation

``` text
A_sig z_i - c_i t_i = w_i mod q_s.
```

This exact relation replaces the superseded rounded-residual batch
construction.

### 5.4 Randomized batch verification

The batch implementation uses:

``` text
Q_B               = 65537
default r_B        = 6
r_B sweep          = 1, 2, 4, 6
batch sizes        = 1, 2, 5, 10, 25, 50, 100, 200, 300, 500
repetitions/point  = 30
```

For each batch, fresh randomized coefficients are used to aggregate the
individual exact verification relations. The aggregate test is repeated
independently `r_B` times.

The `r_B` sweep is a **performance study only**. The final value of
`r_B` must be selected from the formally justified batch-soundness
target and coefficient domain rather than from runtime alone.

### 5.5 Measured batch crossover

`B_min` denotes the smallest evaluated batch size for which randomized
batch verification is faster than independent verification.

    `r_B`   Evaluated batch range   Measured `B_min`
  ------- ----------------------- ------------------
        1                  1--500                  2
        2                  1--500                  5
        4                  1--500                 25
        6                  1--500       No crossover

The results show that increasing the number of independent aggregate
tests increases verification cost. In particular, no performance
crossover was observed for `r_B = 6` through `B = 500`. These
measurements characterize implementation performance and do not
independently establish a cryptographic security level.

### 5.6 Recursive invalid-request localization

When an aggregate verification fails, the affected batch is divided into
approximately equal subsets. Each tested subset uses fresh randomized
coefficients. Failed subsets are recursively partitioned until invalid
singleton requests can be confirmed by individual verification.

The experiment evaluates `B = 10, 25, 50, 100` with invalid-request
ratios of `0%, 5%, 10%, 20%, 30%`.

      B   Invalid (%)       Latency (ms)   Calls / Depth   Throughput (auth/s)
  ----- ------------- ------------------ --------------- ---------------------
     10             0     17.96 +/- 0.32     1.00 / 0.00                557.02
     10             5     41.24 +/- 3.71     7.80 / 3.40                244.37
     10            10     42.38 +/- 6.66     7.53 / 3.27                240.40
     10            20     39.44 +/- 6.62    11.20 / 3.77                261.05
     10            30     34.58 +/- 6.32    13.07 / 3.73                300.18
     25             0     34.08 +/- 4.11     1.00 / 0.00                740.52
     25             5     68.74 +/- 3.74    10.20 / 4.60                364.73
     25            10     71.45 +/- 9.10    16.47 / 4.93                356.29
     25            20    85.41 +/- 11.46    28.27 / 5.00                297.91
     25            30    87.20 +/- 10.07    35.60 / 5.00                290.46
     50             0     62.96 +/- 7.06     1.00 / 0.00                800.78
     50             5   131.03 +/- 18.75    20.53 / 6.00                389.13
     50            10   145.80 +/- 20.13    36.47 / 6.00                349.56
     50            20   173.38 +/- 21.07    55.93 / 6.00                292.06
     50            30   166.37 +/- 14.52    68.67 / 6.00                302.71
    100             0    118.41 +/- 3.72     1.00 / 0.00                845.25
    100             5   241.93 +/- 23.54    46.13 / 7.00                417.35
    100            10   283.52 +/- 20.22    73.20 / 7.00                354.40
    100            20   325.73 +/- 23.44   111.40 / 7.00                308.50
    100            30   341.47 +/- 25.58   139.73 / 7.00                294.33

Latency is mean +/- standard deviation over 30 repetitions.
`Calls / Depth` gives the mean randomized verification-call count and
mean maximum recursion depth.

All evaluated configurations achieved **100% invalid-request isolation
in the experimental runs**. This is an empirical result and must not be
interpreted as an absolute cryptographic guarantee.

### 5.7 Reference communication sizes

  Field               Bytes
  ----------------- -------
  `w_i`                2944
  `z_i`                3680
  `c_i`                  44
  `sigma_i` total      6668
  `t_i`                2944

These values are reference/prototype serialization sizes rather than
optimized production encodings. Consequently, communication values from
the superseded authentication representation must not be reused as
measurements for this revised signature format.

### 5.8 Running the revised authentication experiment

Run:

``` bash
python DTLBA_module_lattice_batch_v4.py
```

The script first executes self-tests and then runs the default
scalability benchmark, the `r_B` sweep, recursive invalid-request
localization, and communication-size calculation.

Principal outputs are:

``` text
batch_scalability_raw_v3.csv
batch_scalability_summary_v3.csv
batch_rB_sweep_raw_v4.csv
batch_rB_sweep_summary_v4.csv
batch_rB_crossover_v4.csv
batch_rB_sweep_summary_v4.txt
invalid_batch_raw_v3.csv
invalid_batch_summary_v3.csv
signature_communication_v3.csv
DTLBA_v3_summary.txt
```

The `v3`/`v4` suffixes identify experimental-script/output revisions;
they do not denote different cryptographic security levels.

### 5.9 Security and interpretation limitations

The Python implementation is a reference performance implementation
rather than an audited cryptographic library. In particular:

-   the custom `(w,z,c)` authentication mechanism requires a complete
    unforgeability/security reduction before it is treated as a
    finalized primitive;
-   the coefficient domain and randomized batch-soundness argument must
    be defined formally;
-   `Q_B = 65537` and the tested `r_B` values do not by themselves
    establish a target security level;
-   the rejection-sampling and concrete lattice-hardness analyses must
    match the final construction;
-   the authentication parameters must not be described as an ML-DSA
    parameter set;
-   experimental 100% invalid-request isolation is not an absolute
    cryptographic guarantee.

Performance measurements and formal security claims must therefore
remain clearly separated.

------------------------------------------------------------------------

## 6. Experiment 3: End-to-End Density Evaluation

### 6.1 Purpose

`DTLBA_end_to_end_density_v1.py` studies the behavior of the
authentication framework as vehicular load increases.

The evaluated density cases are:

``` text
50, 100, 200, 400, and 800 vehicles
```

The experiment combines:

1.  mobility/handover information from the SUMO experiment;
2.  DTLBA processing operations from the reference benchmark;
3.  a packet-level communication model.

The communication model includes serialization, propagation delay,
MAC/access delay, jitter, FCFS contention, packet loss, and
retransmission behavior.

### 6.2 Communication configuration

The included experiment uses:

``` text
Vehicle densities             = 50, 100, 200, 400, 800
Independent repetitions       = 30
Data rate                     = 10.0 Mbps
Propagation delay             = 0.05 ms
Base MAC/access delay         = 0.30 ms
Jitter standard deviation     = 0.15 ms
Packet-loss scenario          = 0.50% to 5.00%
Maximum retransmissions       = 3
Authentication event rate     = 0.02 events/vehicle/s
```

The packet-loss profile is an explicit simulation scenario. It should
not be represented as a measured loss profile from a physical radio
network.

### 6.3 Running the end-to-end experiment

The following files should be in the same working directory:

``` text
DTLBA_end_to_end_density_v1.py
DTLBA_module_lattice_batch_v4.py
dt_handover_events_v2.csv
```

Run:

``` bash
python DTLBA_end_to_end_density_v1.py
```

The default output directory is:

``` text
e2e_density_results/
```

To rerun the SUMO mobility stage before the end-to-end experiment, use:

``` bash
python DTLBA_end_to_end_density_v1.py --run-sumo
```

For this mode, the mobility script and its required SUMO network/route
files must also be available.

### 6.4 End-to-end outputs

The experiment produces:

-   `e2e_density_overall.csv` -- aggregate mean/standard-deviation
    results by density;
-   `e2e_density_repetitions.csv` -- repetition-level measurements;
-   `e2e_density_communication.csv` -- communication-model measurements;
-   `e2e_density_summary.txt` -- experiment configuration summary;
-   `fig_e2e_latency_vs_density.png`;
-   `fig_e2e_components_vs_density.png`;
-   `fig_e2e_throughput_vs_density.png`;
-   `fig_e2e_packet_loss_vs_density.png`.

### 6.5 Included aggregate results

  -----------------------------------------------------------------------------------
    Vehicles Full DTLBA   NoDT E2E  DT latency        Critical Auth. load   Empirical
                    E2E    latency   reduction   communication   (auth/s) packet loss
                latency       (ms)                latency (ms)            
                   (ms)                                                   
  ---------- ---------- ---------- ----------- --------------- ---------- -----------
          50     10.283     20.907      50.82%           9.834       1.00       0.40%

         100     10.328     21.132      51.13%           9.875       2.02       0.93%

         200     10.513     21.753      51.67%          10.065       3.86       1.16%

         400     10.852     23.264      53.35%          10.407       8.18       2.50%

         800     11.680     27.335      57.27%          11.235      16.00       4.92%
  -----------------------------------------------------------------------------------

Full-DTLBA end-to-end latency increases from approximately 10.283 ms at
the lowest evaluated density to 11.680 ms at the highest density. The
corresponding NoDT latency increases from approximately 20.907 ms to
27.335 ms. Within the configured model, the relative benefit of
predictive preparation therefore increases with load.

The increase in end-to-end latency at high density is primarily
associated with the simulated communication component rather than a
large increase in the measured/reference cryptographic processing
component.

### 6.6 Meaning of authentication load

The `auth/s` quantity in the density experiment must be interpreted as
the **offered/processed authentication-event load generated by the
experiment**, not the maximum cryptographic throughput of DTLBA.

The configured arrival rate is:

``` text
0.02 authentication events per vehicle per second
```

Consequently, the increasing `auth/s` values primarily reflect the
increasing number of vehicles. Maximum verification throughput is
evaluated separately in the ablation/batch experiment.

### 6.7 Communication-model limitation

The end-to-end communication latency is **packet-level simulated**. It
is not measured using a physical IEEE 802.11p, C-V2X, 5G NR-V2X, or
other radio testbed.

Accordingly, manuscript wording should use expressions such as:

> "packet-level simulated communication latency"

or:

> "end-to-end latency under the configured communication model"

and should avoid describing these values as physical-radio measurements.

------------------------------------------------------------------------

## 7. Reproducibility Workflow

For a clean reproduction of the principal experiments, use the following
order.

### Step 1 -- Run SUMO mobility prediction

``` bash
python DTLBA_dt_prediction_mobility_v2.py
```

Verify that the following files are generated:

``` text
dt_prediction_events_v2.csv
dt_handover_events_v2.csv
dt_step_metrics_v2.csv
dt_rsu_locations_v2.csv
dt_summary_v2.csv
```

### Step 2 -- Run the revised authentication/batch benchmark

``` bash
python DTLBA_module_lattice_batch_v4.py
```

Check `batch_rB_sweep_summary_v4.csv`, `batch_rB_crossover_v4.csv`,
`invalid_batch_summary_v3.csv`, `signature_communication_v3.csv`, and
`DTLBA_v3_summary.txt`.

### Step 3 -- Run the density experiment

``` bash
python DTLBA_end_to_end_density_v1.py
```

Check `e2e_density_results/e2e_density_overall.csv` and the generated
figures.

### Step 4 -- Preserve raw outputs

For publication/reviewer reproducibility, preserve:

-   the scripts used for the reported run;
-   SUMO network and route files;
-   raw event-level CSVs;
-   repetition-level benchmark CSVs;
-   aggregate CSVs;
-   generated figures;
-   Python version;
-   SUMO version;
-   NumPy/Matplotlib versions;
-   operating system;
-   processor/RAM;
-   random seeds;
-   compiler/library information for any separate C++ implementation.

Do not retain only manuscript tables; the raw CSV files are necessary to
audit how aggregate values were obtained.

------------------------------------------------------------------------

## 8. CSV File Descriptions

### `dt_prediction_events_v2.csv`

Contains individual DT prediction events and their final outcomes. This
is the principal source for prediction accuracy, false-prefetch
behavior, prediction lead time, and unresolved-event analysis.

### `dt_handover_events_v2.csv`

Contains actual RSU transition events observed in SUMO. This file is the
ground-truth handover source used to determine whether a prior DT
prediction was correct.

### `dt_step_metrics_v2.csv`

Contains simulation-step statistics and is useful for examining the
number of active vehicles and time-varying mobility/load conditions.

### `dt_rsu_locations_v2.csv`

Contains the RSU locations selected by the mobility experiment.

### `dt_summary_v2.csv`

Contains the aggregate DT prediction results reported in the manuscript.

### `batch_scalability_raw_v3.csv`

Contains repetition-level individual-versus-batch verification
measurements using the default `r_B`.

### `batch_scalability_summary_v3.csv`

Contains mean and standard-deviation scalability measurements for the
default `r_B`.

### `batch_rB_sweep_raw_v4.csv`

Contains repetition-level measurements for every evaluated `(r_B, B)`
combination.

### `batch_rB_sweep_summary_v4.csv`

Contains summarized individual and randomized batch-verification
timings, throughput, and acceptance results for each `(r_B, B)`
combination.

### `batch_rB_crossover_v4.csv`

Contains the measured crossover `B_min` for each evaluated `r_B`.

### `invalid_batch_raw_v3.csv`

Contains repetition-level recursive invalid-request localization
measurements.

### `invalid_batch_summary_v3.csv`

Contains summarized latency, verification-call count, recursion depth,
throughput, and isolation-success measurements.

### `signature_communication_v3.csv`

Contains reference serialization sizes for `w_i`, `z_i`, `c_i`,
`sigma_i`, and `t_i`.

### `DTLBA_v3_summary.txt`

Contains the authentication parameters, default batch configuration,
measured crossover summary, and implementation caution.

### `e2e_density_overall.csv`

Contains the aggregate results for each vehicle-density condition,
including processing, communication, end-to-end latency, authentication
load, packet loss, and DT latency reduction.

### `e2e_density_repetitions.csv`

Contains repetition-level end-to-end results and should be retained for
statistical verification.

### `e2e_density_communication.csv`

Contains the packet-level communication simulation measurements.

------------------------------------------------------------------------

## 9. Experimental Interpretation

The three experiments answer different performance questions and should
not be mixed:

-   **DT prediction experiment:** How accurately and how early can the
    next RSU be predicted?
-   **Ablation experiment:** What is the contribution of DT preparation
    and batch verification to protocol processing?
-   **Density experiment:** How does end-to-end latency change when
    vehicular and communication load increase?

Together, they provide mobility, component-wise, scalability, and
communication-load evidence for the revised DTLBA evaluation.

------------------------------------------------------------------------

## 10. Important Scientific Caveats

### 10.1 MLWR security level

The parameter tuple `N=512, K=3, q=12289, p=256` is used consistently in
the Python ablation experiment. Consistency is useful for fair internal
comparison, but these values alone do not prove a specific post-quantum
security level.

A final security-level statement should be supported by the finalized
MLWR problem definition, secret/error distributions, reconciliation
construction, failure probability, and concrete security/hardness
analysis.

### 10.2 Reference arithmetic

The included Python MLWR benchmark is intended for
operation-level/reference performance analysis. It should not be
represented as an audited or standards-compliant implementation unless
the underlying arithmetic, reconciliation, signature construction, and
parameterization have been finalized and independently validated.

### 10.3 Batch verification

The revised batch benchmark uses the exact module-lattice verification
relation rather than the superseded rounded-residual verifier. The
measured `B_min` values quantify implementation crossover only.
Cryptographic batch soundness, the coefficient domain, repetition count
`r_B`, and the corresponding cancellation/false-acceptance bound are
separate mathematical requirements that must be justified by the final
protocol and security analysis.

### 10.4 Communication simulation

Wireless communication delay is simulated under explicit assumptions.
The results therefore characterize the configured scenario rather than
all possible V2X networks.

### 10.5 Reproducibility versus external comparison

Using the same cryptographic parameters and platform across Full DTLBA,
NoDT, and NoBatch provides an internally controlled comparison.
Comparisons with external schemes require equivalent security-strength
assumptions and, ideally, uniform implementations or clearly identified
operation-count estimates.

------------------------------------------------------------------------

## 11. Suggested Citation of Results in the Manuscript

When reporting the package results, the following distinctions are
recommended:

-   report DT prediction accuracy together with prediction
    resolution/coverage;
-   report batch throughput separately from density-experiment
    authentication load;
-   report mean values together with standard deviation where available;
-   identify the number of repetitions (`30`);
-   identify the vehicle-density cases (`50, 100, 200, 400, 800`);
-   explicitly state that communication delay is packet-level simulated;
-   state that the same MLWR parameters are used across DTLBA ablation
    variants;
-   avoid claiming a NIST security category until concrete MLWR security
    estimation is supplied.

------------------------------------------------------------------------

## 12. Troubleshooting

### `SUMO_HOME is not set`

Set the SUMO installation directory in the environment before running
the mobility script.

### TraCI import error

Verify that:

``` text
$SUMO_HOME/tools
```

exists and that the installed SUMO version includes the Python TraCI
tools.

### Missing `hyd.net.xml` or `routes.rou.xml`

Run the mobility script from the directory containing these files or
update the corresponding configuration paths in the script.

### Missing `dt_handover_events_v2.csv`

Run the DT mobility experiment first. The handover CSV is used by the
subsequent experiments.

### End-to-end script cannot find the v3 benchmark

Keep `DTLBA_module_lattice_batch_v4.py` beside
`DTLBA_end_to_end_density_v1.py`, or provide the path through the
supported command-line argument.

### Results differ slightly between systems

Runtime measurements may vary with processor frequency scaling,
background processes, Python/NumPy versions, and operating-system
scheduling. Use the same software/hardware environment and repeat the
experiment before comparing numerical timing results.

------------------------------------------------------------------------

## 13. Reproducibility Checklist

Before releasing the package with the manuscript, confirm the following:

-   [ ] SUMO version is documented.
-   [ ] Python version is documented.
-   [ ] NumPy and Matplotlib versions are documented.
-   [ ] Operating system is documented.
-   [ ] Hardware specification is documented.
-   [ ] Random seed(s) are documented.
-   [ ] `SUMO_HOME` setup instructions are correct.
-   [ ] Network and route files required by the scripts are included.
-   [ ] All reported CSV outputs can be regenerated.
-   [ ] All manuscript figures can be regenerated from the supplied
    outputs.
-   [ ] The C++/OpenSSL/NTL source and build details are included if C++
    timing claims remain in the manuscript.
-   [ ] MLWR security parameters match the final manuscript.
-   [ ] Reconciliation/signature implementation matches the final
    protocol.
-   [ ] Communication results are explicitly identified as simulated
    rather than physical-radio measured.
-   [ ] External-scheme comparisons use equivalent security assumptions
    or are clearly identified as analytical estimates.

------------------------------------------------------------------------

## 14. Summary

This package provides a reproducible experimental workflow for
evaluating DTLBA across **digital-twin mobility prediction,
component-wise ablation, batch scalability, and end-to-end communication
load**. The included SUMO experiment records actual mobility and RSU
transitions, the revised authentication benchmark evaluates exact
individual verification, randomized batch scalability, crossover
behavior, and recursive invalid-request localization, and the density
experiment evaluates end-to-end behavior from 50 to 800 vehicles under
explicitly defined communication assumptions.

The raw CSV files should be treated as the authoritative experiment
outputs. Aggregate manuscript tables and figures should be regenerated
from these files whenever the implementation or protocol parameters are
changed.
