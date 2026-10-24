# Source Verification Log

Comprehensive evidence log of external data sources verified via live HTTP requests and code execution, pursuant to Section 1.2 and Phase 1 of the Integrity Contract.

**Verification Date (UTC):** 2026-10-23
**Verified By:** Autonomous Pipeline Pre-Flight Checks

---

## 1. Electricity Demand: Grid-India (formerly POSOCO / NLDC)

### 1.1 Website & Portal Discovery
* **Official Primary Domain:** `https://grid-india.in` (Grid Controller of India Limited)
* **Legacy Domain:** `https://posoco.in` — Probed via HTTP GET. Returned `HTTP 502 Bad Gateway` (domain deprecated/non-functional).
* **Robots.txt:** `https://grid-india.in/robots.txt`
  * Retrieval Status: `HTTP 200`
  * Content: Single Page Application (SPA) index shell serving Vue/React frontend (`/assets/index-CO5t6Yxl.js`). No Disallow directives forbidding automated access to public IEGC regulatory reports.
* **Terms of Use / Mandate:** Published pursuant to Article 5.5.1 of the Indian Electricity Grid Code (IEGC) mandated by Central Electricity Regulatory Commission (CERC) for public transparency.

### 1.2 Backend API Discovery
Inspection of the client-side bundle (`/assets/index-CO5t6Yxl.js`) revealed dedicated REST API endpoints:
* **Base URL:** `https://webapi.grid-india.in/api/v1/`
* **CDN File Host:** `https://webcdn.grid-india.in/`
* **Period Discovery Endpoint:** `POST https://webapi.grid-india.in/api/v1/file/get-period`
  * Payload: `{"_source": "grdw", "_fileType": "DAILY_PSP_REPORT"}`
  * HTTP Status: `200 OK`
  * Result: Returned 15 operational periods: `2010-11`, `2013-14`, `2014-15`, `2015-16`, `2016-17`, `2017-18`, `2018-19`, `2019-20`, `2020-21`, `2021-22`, `2022-23`, `2023-24`, `2024-25`, `2025-26`, `2026-27`.
* **File Metadata Endpoint:** `POST https://webapi.grid-india.in/api/v1/file`
  * Payload: `{"_source": "grdw", "_type": "DAILY_PSP_REPORT", "_fileDate": "<period>", "_month": "<mm>"}`
  * HTTP Status: `200 OK`
  * Result: Returns exact file paths, mime types (`attachment/pdf`, `attachment/xls`), file sizes, and reporting dates.

### 1.3 Sample Files Probed Across Years
20 sample files across 10 distinct periods were downloaded and verified:

| Period | Sample File Title | Format | HTTP Status | Size (Bytes) | SHA256 (First 16 chars) | Pages | States Found |
|---|---|---|---|---|---|---|---|
| 2014-15 | 31.05.14_NLDC_PSP | PDF | 200 | 81,207 | 3bb31e5f039405ae | 2 | 8 |
| 2014-15 | 30.05.14_NLDC_PSP | PDF | 200 | 93,715 | e3f10137d6e810eb | 2 | 8 |
| 2016-17 | 31.05.16_NLDC_PSP | PDF | 200 | 933,712 | 024467c6999b9cf9 | 3 | 8 |
| 2016-17 | 30.05.16_NLDC_PSP | PDF | 200 | 392,465 | d2ad66f5713404c0 | 3 | 8 |
| 2018-19 | 31.05.18_NLDC_PSP | PDF | 200 | 1,604,166 | de0bb2a74c39999a | 3 | 8 |
| 2018-19 | 30.05.18_NLDC_PSP | PDF | 200 | 1,695,505 | 224b7a1104e76868 | 3 | 8 |
| 2019-20 | 30.05.19_NLDC_PSP | PDF | 200 | 1,495,709 | f5a0c9610fba3eb2 | 3 | 8 |
| 2020-21 | 31.05.20_NLDC_PSP | PDF | 200 | 1,231,655 | 696bb337a7267eb4 | 3 | 8 |
| 2020-21 | 30.05.20_NLDC_PSP | PDF | 200 | 1,505,410 | b368ebf94e9f7a7d | 3 | 8 |
| 2021-22 | 31.05.21_NLDC_PSP | PDF | 200 | 1,328,280 | fb2974b6df00d453 | 5 | 7 |
| 2021-22 | 30.05.21_NLDC_PSP | PDF | 200 | 1,239,332 | be3ce65b16f6b5b2 | 3 | 8 |
| 2022-23 | 31.05.22_NLDC_PSP | PDF | 200 | 315,258 | 8b5c9ea00c9ea451 | 3 | 8 |
| 2022-23 | 30.05.22_NLDC_PSP | PDF | 200 | 315,145 | f251147040b2efb4 | 3 | 8 |
| 2023-24 | 31.05.23_NLDC_PSP | PDF | 200 | 335,043 | 9035a9f60cb053ea | 3 | 8 |
| 2023-24 | 30.05.23_NLDC_PSP | PDF | 200 | 332,773 | 7efba4c81f33bf9c | 3 | 8 |
| 2024-25 | 31.05.24_NLDC_PSP | PDF | 200 | 300,512 | b9f8605c2195f171 | 4 | 8 |
| 2024-25 | 30.05.24_NLDC_PSP | PDF | 200 | 300,142 | c3f82522c069502c | 4 | 8 |
| 2025-26 | 31.05.25_NLDC_PSP | PDF | 200 | 2,113,584 | b1e15b369ba01dc7 | 5 | 8 |
| 2025-26 | 30.05.25_NLDC_PSP | PDF | 200 | 1,741,120 | 20973a871587a892 | 5 | 8 |

---

## 2. Weather: Open-Meteo Historical Weather API

* **Endpoint:** `https://archive-api.open-meteo.com/v1/archive`
* **Nature of Data:** Reanalysis-based gridded data (ECMWF ERA5 / ERA5-Land), **not** physical ground weather station observations.
* **Temporal Resolution:** Daily aggregates computed from hourly reanalysis.
* **Parameters Tested:**
  * `latitude`, `longitude`: Decimal degrees
  * `daily`: `temperature_2m_max`, `temperature_2m_min`, `temperature_2m_mean`, `apparent_temperature_max`, `relative_humidity_2m_mean`, `precipitation_sum`
  * `timezone`: `Asia/Kolkata`
* **Units Returned:**
  * Temperatures: `°C`
  * Relative Humidity: `%`
  * Precipitation: `mm`
* **Live Test Outcome:** 16 calls across all 16 state centroids returned `HTTP 200` with non-empty arrays and zero null values. Average response latency: ~1.2 seconds.
* **Terms & Licensing:** Open-Meteo is free for non-commercial open-source research and educational use under Creative Commons Attribution 4.0 International (CC BY 4.0), requiring explicit attribution: *"Weather data by Open-Meteo.com"*.

---

## 3. Calendar & Holidays: `holidays` Python Package

* **Package Version:** `holidays 0.107`
* **Subdivision Support:** Covers all 36 Indian states and Union Territories (`AN`, `AP`, `AR`, `AS`, `BR`, `CG`, `CH`, `DH`, `DL`, `GA`, `GJ`, `HP`, `HR`, `JH`, `JK`, `KA`, `KL`, `LA`, `LD`, `MH`, `ML`, `MN`, `MP`, `MZ`, `NL`, `OD`, `PB`, `PY`, `RJ`, `SK`, `TN`, `TR`, `TS`, `UK`, `UP`, `WB`).
* **National Coverage:** Covers statutory national holidays (Republic Day, Independence Day, Mahatma Gandhi Jayanti) and major religious/cultural festivals across all tested years (2019–2024).
* **Documented Limitation:** Does not capture ad-hoc local bank holidays or state-specific administrative non-working days declared via ad-hoc gazette notifications.

---

## 4. Geographic Centroid Plausibility Check

All 16 representative state coordinates in `config.yaml` passed boundary verification:
* Latitudes: All within mainland India bounds ($8.0^\circ\text{N} \le \text{lat} \le 37.5^\circ\text{N}$)
* Longitudes: All within mainland India bounds ($68.0^\circ\text{E} \le \text{lon} \le 97.5^\circ\text{E}$)
* Points correspond to verified state capital or primary industrial/urban load centre.
