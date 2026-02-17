-- =============================================================================
-- Model Evaluation Queries
-- Run these individually in BigQuery console for detailed model analysis
-- =============================================================================

-- Query 1: Training Statistics
-- Shows training convergence and iterations
SELECT * FROM ML.TRAINING_INFO(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY iteration;


-- Query 2: Model Metrics
-- Classification metrics: accuracy, precision, recall, AUC-ROC
SELECT * FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);


-- Query 3: Confusion Matrix
SELECT * FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.gold_user_retention_model`);


-- Query 4: ROC Curve Data
SELECT * FROM ML.ROC_CURVE(MODEL `propensity_modeling.gold_user_retention_model`);


-- Query 5: Feature Importance (Global Explain)
-- Shows which features drive predictions
SELECT * FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC;


-- Query 6: Model Weights
-- Shows learned coefficients for logistic regression
SELECT * FROM ML.WEIGHTS(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY ABS(weight) DESC;
