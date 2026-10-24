# Electricity Demand Source Report: Grid-India Daily PSP Reports

**Document Version:** 1.0  
**Retrieval & Analysis Date (UTC):** 2026-10-23  
**Integrity Protocol:** Based entirely on empirical inspection of fetched files from Grid-India / NLDC.

---

## 1. Executive Summary & Granularity

* **Publishing Organization:** Grid Controller of India Limited (Grid-India), formerly Power System Operation Corporation Limited (POSOCO).
* **Compiling Body:** National Load Despatch Centre (NLDC), New Delhi.
* **Granularity Available:**
  * **Temporal:** Daily (aggregating the 24-hour dispatch day, typically 00:00 to 24:00 hrs of previous day).
  * **Spatial:** State-level across all 5 regional grids (Northern, Western, Southern, Eastern, North Eastern) plus regional summaries and All-India total.
* **Available Date Range:**
  * Earliest archive record in portal: `2010-11` (sparse) and continuous from `2013-14` onward.
  * Modern standardized digital format: Available daily from `2019` to current date.
* **Available Formats:**
  * Both **PDF** (`attachment/pdf`) and **Excel XLS** (`attachment/xls`) are published concurrently for every operating day via `https://webcdn.grid-india.in/`.

---

## 2. Meaning of Quantities and Engineering Metrics

Based on the official definitions in the Indian Electricity Grid Code (IEGC) and NLDC report headers:

1. **"Max. Demand Met during the day (MW)":**
   * **Definition:** The instantaneous or 15-minute time-block maximum electrical load served by the grid within that state during the 24 hours.
   * **Measurement Method:** Telemetry-derived from **NLDC / RLDC SCADA** systems measuring actual active power flow across inter-state transmission system (ISTS) interconnection points and state generation telemetry.
   * **Relationship to "True Peak Demand":** Max Demand Met represents **actual unconstrained demand met** *minus* any involuntary load curtailment or statutory power cuts.
2. **"Shortage during maximum Demand (MW)":**
   * **Definition:** Unmet load due to generation deficits, transmission bottlenecks, or regulatory load shedding occurring at the moment of the day's maximum demand.
   * **Unrestricted Peak Demand Calculation:**
     $$\text{True Peak Demand (MW)} = \text{Max Demand Met (MW)} + \text{Shortage during Max Demand (MW)}$$
     *(Note: In contemporary Indian grid operations, especially post-2021 across major industrial states, Shortage during Maximum Demand is frequently 0 MW due to adequate resource adequacy, though isolated shortages occur during extreme heat spikes).*
3. **"Energy Met (MU)":**
   * Total electrical energy consumed/supplied within the state during the entire day, measured in Million Units (1 MU = 1 Gigawatt-hour = $10^6\text{ kWh}$).
4. **"Time of Maximum Demand Met":**
   * The All-India report lists the exact time of maximum demand met at the **Regional** level and **All-India** level (e.g. `14:59 hrs` All-India, `19:52 hrs` NR, `15:12 hrs` WR) in Section A of Page 2.
   * **Individual state-level peak timestamps:** **UNKNOWN** in the daily PSP PDF (the PDF provides state-level peak magnitude in MW, while regional and national peak timestamps are explicitly given; state-level 15-minute load curves are retained internally by State Load Despatch Centres (SLDCs)).

---

## 3. State Coverage and Entity Evolution Across Years

Inspection of sample files reveals the following historical entity transitions:

1. **Andhra Pradesh / Telangana Bifurcation (2014):**
   * Pre-June 2014 reports list unified `Andhra Pradesh`.
   * From June 2014 onward, `Andhra Pradesh` and `Telangana` are reported as distinct state rows.
2. **Dadra and Nagar Haveli and Daman and Diu Merger (2020):**
   * Pre-2020 reports list `DD` (Daman and Diu) and `DNH` (Dadra and Nagar Haveli) separately.
   * Post-merger reports list the combined distribution entity `DNHDDPDCL` in the Western Region.
3. **Jammu & Kashmir / Ladakh Reorganization (2019):**
   * Pre-August 2019 reports list `J&K`.
   * Post-August 2019 reports list `J&K(UT) & Ladakh(UT)`.
4. **Industrial Embedded Entities:**
   * Certain industrial and railway bulk consumers (`Essar Steel / AMNSIL`, `BALCO`, `Railways_NR ISTS`, `DVC`) appear as dedicated rows in regional sections. These are industrial drawing entities and are separated from state administrative boundaries during cleaning.

---

## 4. Final Selected State Scope and Period Rationale

To ensure 100% genuine data, uniform geographic definitions, and avoidance of structural breaks:
* **Selected Period:** 5 Continuous Years: **2019-01-01 to 2024-12-31** (spanning over 2,100 days).
* **Selected States (16 Major Indian States):**
  * **Northern Region:** Delhi, Punjab, Haryana, Rajasthan, Uttar Pradesh
  * **Western Region:** Maharashtra, Gujarat, Madhya Pradesh
  * **Southern Region:** Tamil Nadu, Karnataka, Telangana, Andhra Pradesh, Kerala
  * **Eastern Region:** West Bengal, Bihar, Odisha
* **Representativeness:** These 16 states account for >85% of India's total electricity consumption and provide complete geographical, economic, and climatic diversity (tropical coastal, arid desert, Indo-Gangetic plains, Deccan plateau).

---

## 5. Secondary Sources Evaluation

* **Central Electricity Authority (CEA) Monthly Executive Summaries:** Verified via CEA website. CEA publishes monthly aggregates (energy and peak met) with a 1-2 month reporting lag. Because the primary Grid-India PSP reports provide daily resolution directly from SCADA, CEA reports serve as benchmark reconciliation rather than primary ingestion.
* **data.gov.in / National Data Sharing Platform:** Hosts sporadic historical electricity snapshots, but lacks daily automated live feeds matching NLDC daily releases.
* **State Load Despatch Centre (SLDC) Portals:** Highly heterogeneous formats across states (some behind CAPTCHA or broken portals). Grid-India's national PSP compiles all SLDC telemetry into a single authoritative regulatory standard, eliminating multi-portal inconsistency.
