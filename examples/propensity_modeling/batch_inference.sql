-- Score hypothetical user
SELECT
    predicted_will_return,
    ROUND(
        predicted_will_return_probs [OFFSET(1)].prob,
        3
    ) AS return_probability,
    ROUND(
        predicted_will_return_probs [OFFSET(0)].prob,
        3
    ) AS churn_probability
FROM
    ml.predict(
        model `propensity_modeling.gold_user_retention_model`,
        (
            SELECT
                7 AS days_in_window,
                2 AS days_active,
                20 AS total_events,
                3 AS levels_started,
                1 AS levels_completed,
                5.0 AS total_engagement_minutes,
                75 AS max_score,
                2.9 AS events_per_day,
                0.7 AS engagement_minutes_per_day,
                0.33 AS level_completion_rate,
                10.0 AS events_per_active_day,
                4 AS days_since_last_activity,
                'mobile' AS device_category,
                'Android' AS operating_system,
                'Brazil' AS country
        )
    );
-- Score all users
SELECT
    user_pseudo_id,
    observation_date,
    predicted_will_return,
    ROUND(
        predicted_will_return_probs [OFFSET(1)].prob,
        3
    ) AS return_probability,
    ROUND(
        predicted_will_return_probs [OFFSET(0)].prob,
        3
    ) AS churn_probability
FROM
    ml.predict(
        model `propensity_modeling.gold_user_retention_model`,
        (
            SELECT
                days_in_window,
                days_active,
                total_events,
                levels_started,
                levels_completed,
                total_engagement_minutes,
                max_score,
                events_per_day,
                engagement_minutes_per_day,
                level_completion_rate,
                events_per_active_day,
                days_since_last_activity,
                device_category,
                operating_system,
                country
            FROM
                `propensity_modeling.gold_training_features`
        )
    )
ORDER BY
    churn_probability DESC;
