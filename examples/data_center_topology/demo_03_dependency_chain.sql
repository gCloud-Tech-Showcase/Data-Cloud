-- =============================================================================
-- DEMO 03: Application Dependency Chain Analysis
-- =============================================================================
-- These queries demonstrate multi-hop dependency traversal:
-- "If App A fails, what downstream apps are affected?"
-- "What are all the upstream dependencies of App A?"
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Direct Dependencies Overview
-- Show applications and their immediate dependencies
-- -----------------------------------------------------------------------------
SELECT
  a1.app_name AS application,
  a1.criticality_tier,
  a1.app_type,
  STRING_AGG(
    CONCAT(a2.app_name, ' (', ad.dependency_type, IF(ad.is_critical, ', CRITICAL', ''), ')'),
    ', '
  ) AS depends_on,
  COUNT(ad.dependency_id) AS dependency_count,
  COUNTIF(ad.is_critical) AS critical_dependencies
FROM `data_center_topology.applications` a1
LEFT JOIN `data_center_topology.app_dependencies` ad ON a1.app_id = ad.app_id
LEFT JOIN `data_center_topology.applications` a2 ON ad.depends_on_app_id = a2.app_id
GROUP BY a1.app_id, a1.app_name, a1.criticality_tier, a1.app_type
ORDER BY critical_dependencies DESC, dependency_count DESC;

-- -----------------------------------------------------------------------------
-- 2. Downstream Impact (2-hop)
-- If an app fails, what apps directly depend on it AND what depends on those?
-- -----------------------------------------------------------------------------
WITH RECURSIVE downstream_impact AS (
  -- Base case: apps that directly depend on the failing app
  SELECT
    ad.app_id,
    a.app_name,
    ad.depends_on_app_id AS failed_app_id,
    a.criticality_tier,
    ad.is_critical,
    1 AS hop_level,
    ARRAY[a.app_name] AS path
  FROM `data_center_topology.app_dependencies` ad
  JOIN `data_center_topology.applications` a ON ad.app_id = a.app_id
  WHERE ad.depends_on_app_id = (
    SELECT app_id FROM `data_center_topology.applications`
    WHERE app_name = 'auth-service'  -- Replace with app to analyze
    LIMIT 1
  )

  UNION ALL

  -- Recursive case: apps that depend on already-affected apps
  SELECT
    ad.app_id,
    a.app_name,
    di.failed_app_id,
    a.criticality_tier,
    ad.is_critical,
    di.hop_level + 1 AS hop_level,
    di.path || a.app_name
  FROM downstream_impact di
  JOIN `data_center_topology.app_dependencies` ad ON ad.depends_on_app_id = di.app_id
  JOIN `data_center_topology.applications` a ON ad.app_id = a.app_id
  WHERE di.hop_level < 3  -- Limit recursion depth
    AND a.app_name NOT IN UNNEST(di.path)  -- Prevent cycles
)
SELECT
  hop_level,
  app_name,
  criticality_tier,
  is_critical AS critical_dependency,
  ARRAY_TO_STRING(path, ' -> ') AS impact_path
FROM downstream_impact
ORDER BY hop_level, criticality_tier, app_name;

-- -----------------------------------------------------------------------------
-- 3. Upstream Dependencies (2-hop)
-- What does this app depend on, and what do THOSE apps depend on?
-- -----------------------------------------------------------------------------
WITH RECURSIVE upstream_deps AS (
  -- Base case: direct dependencies
  SELECT
    ad.depends_on_app_id AS app_id,
    a.app_name,
    ad.app_id AS dependent_app_id,
    a.criticality_tier,
    ad.dependency_type,
    ad.is_critical,
    1 AS hop_level,
    ARRAY[a.app_name] AS path
  FROM `data_center_topology.app_dependencies` ad
  JOIN `data_center_topology.applications` a ON ad.depends_on_app_id = a.app_id
  WHERE ad.app_id = (
    SELECT app_id FROM `data_center_topology.applications`
    WHERE app_name = 'web-frontend'  -- Replace with app to analyze
    LIMIT 1
  )

  UNION ALL

  -- Recursive case: dependencies of dependencies
  SELECT
    ad.depends_on_app_id AS app_id,
    a.app_name,
    ud.dependent_app_id,
    a.criticality_tier,
    ad.dependency_type,
    ad.is_critical,
    ud.hop_level + 1 AS hop_level,
    ud.path || a.app_name
  FROM upstream_deps ud
  JOIN `data_center_topology.app_dependencies` ad ON ad.app_id = ud.app_id
  JOIN `data_center_topology.applications` a ON ad.depends_on_app_id = a.app_id
  WHERE ud.hop_level < 3
    AND a.app_name NOT IN UNNEST(ud.path)
)
SELECT
  hop_level,
  app_name AS upstream_dependency,
  criticality_tier,
  dependency_type,
  is_critical,
  ARRAY_TO_STRING(path, ' <- ') AS dependency_path
FROM upstream_deps
ORDER BY hop_level, criticality_tier, app_name;

-- -----------------------------------------------------------------------------
-- 4. Critical Dependency Chains
-- Find all chains where a non-critical app depends (directly or indirectly)
-- on a critical app - potential blast radius for TIER_1 failures
-- -----------------------------------------------------------------------------
WITH RECURSIVE critical_chains AS (
  -- Start from TIER_1 apps
  SELECT
    a.app_id,
    a.app_name,
    a.criticality_tier,
    ARRAY[a.app_name] AS chain,
    a.app_id AS root_app_id
  FROM `data_center_topology.applications` a
  WHERE a.criticality_tier = 'TIER_1'

  UNION ALL

  -- Find apps that depend on current level
  SELECT
    a.app_id,
    a.app_name,
    a.criticality_tier,
    cc.chain || a.app_name,
    cc.root_app_id
  FROM critical_chains cc
  JOIN `data_center_topology.app_dependencies` ad ON ad.depends_on_app_id = cc.app_id
  JOIN `data_center_topology.applications` a ON ad.app_id = a.app_id
  WHERE ARRAY_LENGTH(cc.chain) < 4
    AND a.app_name NOT IN UNNEST(cc.chain)
    AND ad.is_critical = TRUE
)
SELECT
  (SELECT app_name FROM `data_center_topology.applications` WHERE app_id = root_app_id) AS critical_root,
  ARRAY_LENGTH(chain) - 1 AS chain_length,
  ARRAY_TO_STRING(chain, ' -> ') AS full_chain,
  app_name AS affected_app,
  criticality_tier AS affected_tier
FROM critical_chains
WHERE ARRAY_LENGTH(chain) > 1
ORDER BY root_app_id, ARRAY_LENGTH(chain);

-- -----------------------------------------------------------------------------
-- 5. Circular Dependency Detection
-- Find apps that have circular dependencies (A -> B -> ... -> A)
-- -----------------------------------------------------------------------------
WITH RECURSIVE dep_paths AS (
  SELECT
    ad.app_id AS start_app,
    ad.depends_on_app_id AS current_app,
    ARRAY[ad.app_id, ad.depends_on_app_id] AS path,
    FALSE AS is_cycle
  FROM `data_center_topology.app_dependencies` ad

  UNION ALL

  SELECT
    dp.start_app,
    ad.depends_on_app_id AS current_app,
    dp.path || ad.depends_on_app_id,
    ad.depends_on_app_id = dp.start_app AS is_cycle
  FROM dep_paths dp
  JOIN `data_center_topology.app_dependencies` ad ON ad.app_id = dp.current_app
  WHERE ARRAY_LENGTH(dp.path) < 10
    AND NOT dp.is_cycle
    AND ad.depends_on_app_id NOT IN UNNEST(dp.path[OFFSET(1):])
)
SELECT DISTINCT
  (SELECT app_name FROM `data_center_topology.applications` WHERE app_id = start_app) AS cycle_start,
  ARRAY_LENGTH(path) - 1 AS cycle_length,
  (
    SELECT STRING_AGG(a.app_name, ' -> ' ORDER BY pos)
    FROM UNNEST(path) AS app_id WITH OFFSET pos
    JOIN `data_center_topology.applications` a ON a.app_id = app_id
  ) AS cycle_path
FROM dep_paths
WHERE is_cycle
ORDER BY cycle_length;
