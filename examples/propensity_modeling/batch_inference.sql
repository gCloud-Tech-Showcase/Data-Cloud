-- Score hypothetical user
SELECT
    predicted_will_return,
    ROUND(
        (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1),
        3
    ) AS return_probability,
    ROUND(
        (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 0),
        3
    ) AS churn_probability
FROM
    ml.predict(
        model `propensity_modeling.gold_user_retention_model`,
        (
            SELECT
                7 AS days_in_window,
                5 AS days_active,
                289 AS total_events,
                0 AS levels_started,
                0 AS levels_completed,
                32.7437 AS total_engagement_minutes,
                0 AS max_score,
                41.2857 AS events_per_day,
                4.6777 AS engagement_minutes_per_day,
                0.0 AS level_completion_rate,
                57.8 AS events_per_active_day,
                0 AS days_since_last_activity,
                'mobile' AS device_category,
                'ANDROID' AS operating_system,
                'United States' AS country
        )
    );
-- Score all users
SELECT
    user_pseudo_id,
    observation_date,
    predicted_will_return,
    ROUND(
        (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1),
        3
    ) AS return_probability,
    ROUND(
        (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 0),
        3
    ) AS churn_probability
FROM
    ml.predict(
        model `propensity_modeling.gold_user_retention_model`,
        (
            SELECT
                user_pseudo_id,
                observation_date,
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
