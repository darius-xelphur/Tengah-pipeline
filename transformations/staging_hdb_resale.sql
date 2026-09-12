-- transformations/staging_hdb_resale.sql
-- Purpose: Type-cast raw HDB resale data into staging layer (full truncate-reload)
-- Source: raw.hdb_resale_transactions
-- Target: staging.hdb_resale_transactions
-- Load pattern: full dump — truncate + insert on every run
-- Timezone: all audit timestamps recorded in Singapore time (Asia/Singapore)
-- SCD: Type 2 structure present (valid_from/valid_to/valid) but not yet
--      exercised since this is a full truncate load, not incremental

-- ═══════════════════════════════════════════════════════════════════
-- STEP 1: Create table if it doesn't exist
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS `tengah-analytics.staging.hdb_resale_transactions` (
  surrogate_id            INT64     NOT NULL,
  transaction_month       DATE,
  town                    STRING,
  flat_type               STRING,
  block                   STRING,
  street_name             STRING,
  storey_range            STRING,
  floor_area_sqm          FLOAT64,
  flat_model              STRING,
  lease_commence_date     STRING,
  remaining_lease         STRING,
  resale_price            FLOAT64,

  -- SCD Type 2 tracking columns (Singapore local time)
  valid_from              DATETIME  NOT NULL,
  valid_to                DATETIME  NOT NULL,
  change_time             DATETIME  NOT NULL,
  valid                   INT64     NOT NULL
);

-- ═══════════════════════════════════════════════════════════════════
-- STEP 2: Truncate + reload
-- ═══════════════════════════════════════════════════════════════════

TRUNCATE TABLE `tengah-analytics.staging.hdb_resale_transactions`;

INSERT INTO `tengah-analytics.staging.hdb_resale_transactions`

SELECT
  ROW_NUMBER() OVER (
    ORDER BY month, town, flat_type, block, street_name
  )                                          AS surrogate_id,

  PARSE_DATE('%Y-%m', month)                AS transaction_month,
  town                                       AS town,
  flat_type                                  AS flat_type,
  block                                      AS block,
  street_name                                AS street_name,
  storey_range                               AS storey_range,
  CAST(floor_area_sqm AS FLOAT64)            AS floor_area_sqm,
  flat_model                                 AS flat_model,
  CAST(lease_commence_date AS STRING)        AS lease_commence_date,
  remaining_lease                            AS remaining_lease,
  CAST(resale_price AS FLOAT64)              AS resale_price,

  -- SCD Type 2 defaults — Singapore local time
  CURRENT_DATETIME('Asia/Singapore')         AS valid_from,
  DATETIME('9999-12-31 00:00:00')            AS valid_to,
  CURRENT_DATETIME('Asia/Singapore')         AS change_time,
  1                                          AS valid

FROM `tengah-analytics.raw.hdb_resale_transactions`

WHERE
  resale_price IS NOT NULL
  AND floor_area_sqm IS NOT NULL
  AND month IS NOT NULL;