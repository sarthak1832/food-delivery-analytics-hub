USE food_db;

-- SECTION 1: BASIC OVERVIEW QUERIES

-- 1.1 Total summary stats
SELECT
COUNT(*) AS total_orders,
ROUND(SUM(cost_of_the_order), 2) AS total_revenue,
ROUND(AVG(cost_of_the_order), 2) AS avg_order_value,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins,
ROUND(AVG(rating), 2) AS avg_rating
FROM food_orders;

-- 1.2 Orders and revenue by cuisine
SELECT cuisine_type,
COUNT(*) AS orders,
ROUND(SUM(cost_of_the_order), 0) AS revenue,
ROUND(AVG(rating), 2) AS avg_rating,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins
FROM food_orders
GROUP BY cuisine_type
ORDER BY orders DESC;

-- 1.3 Weekday vs Weekend comparison
SELECT day_of_the_week,
COUNT(*) AS orders,
ROUND(AVG(cost_of_the_order), 2) AS avg_order_value,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins,
ROUND(AVG(rating), 2) AS avg_rating
FROM food_orders
GROUP BY day_of_the_week;

-- 1.4 Delivery speed breakdown
SELECT time_category,
COUNT(*) AS orders,
ROUND(AVG(cost_of_the_order), 2) AS avg_order_value,
ROUND(AVG(rating), 2) AS avg_rating,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins
FROM food_orders
GROUP BY time_category
ORDER BY FIELD(time_category, 'Fast', 'Normal', 'Slow');

-- SECTION 2: RESTAURANT ANALYSIS

-- 2.1 Top 10 restaurants by performance score
SELECT restaurant_name,total_orders,
ROUND(avg_rating, 2) AS avg_rating,
ROUND(avg_del_time, 1) AS avg_delivery_mins,
ROUND(avg_cost, 2) AS avg_order_value,
ROUND(perf_score, 1) AS performance_score
FROM restaurant_perf
ORDER BY perf_score DESC
LIMIT 10;

-- 2.2 Bottom 10 restaurants (need improvement)
SELECT restaurant_name,total_orders,
ROUND(avg_rating, 2) AS avg_rating,
ROUND(perf_score, 1) AS performance_score
FROM restaurant_perf
WHERE total_orders >= 5
ORDER BY perf_score ASC
LIMIT 10;

-- 2.3 High volume but low rating restaurants
SELECT restaurant_name,total_orders,
ROUND(avg_rating, 2) AS avg_rating,
ROUND(perf_score, 1) AS perf_score
FROM restaurant_perf
WHERE total_orders >= 10 AND avg_rating < 3.5
ORDER BY total_orders DESC;

-- 2.4 Best cuisine for each speed category
SELECT time_category,cuisine_type,
COUNT(*) AS orders
FROM food_orders
GROUP BY time_category, cuisine_type
ORDER BY time_category, orders DESC;

-- SECTION 3: WINDOW FUNCTION QUERIES

-- 3.1 Rank restaurants by performance score
SELECT restaurant_name,
ROUND(perf_score, 1) AS perf_score,
RANK() OVER (ORDER BY perf_score DESC) AS perf_rank,
ROUND(PERCENT_RANK() OVER (ORDER BY perf_score) * 100, 1) AS top_percentile
FROM restaurant_perf
ORDER BY perf_rank
LIMIT 20;

-- 3.2 Each restaurant vs overall average delivery time
SELECT restaurant_name,
ROUND(AVG(delivery_time), 1) AS rest_avg_delivery,
ROUND(AVG(AVG(delivery_time)) OVER (), 1) AS platform_avg_delivery,
ROUND(AVG(delivery_time) - AVG(AVG(delivery_time)) OVER (), 1) AS diff_from_avg
FROM food_orders
GROUP BY restaurant_name
ORDER BY diff_from_avg ASC
LIMIT 15;

-- 3.3 Running revenue total by cuisine
SELECT cuisine_type,
ROUND(SUM(cost_of_the_order), 0) AS cuisine_revenue,
SUM(ROUND(SUM(cost_of_the_order), 0))
OVER (ORDER BY SUM(cost_of_the_order) DESC) AS running_total
FROM food_orders
GROUP BY cuisine_type
ORDER BY cuisine_revenue DESC;

-- 3.4 Order value percentile per order
SELECT order_id,restaurant_name,cost_of_the_order,
ROUND(PERCENT_RANK() OVER (ORDER BY cost_of_the_order) * 100, 1) AS value_percentile
FROM food_orders
ORDER BY value_percentile DESC
LIMIT 20;

-- SECTION 4: BUSINESS INSIGHT QUERIES

-- 4.1 What is the peak ordering time (weekend vs weekday per cuisine)?
SELECT day_of_the_week,cuisine_type,
COUNT(*) AS orders
FROM food_orders
GROUP BY day_of_the_week, cuisine_type
ORDER BY day_of_the_week, orders DESC;

-- 4.2 Do rated orders have higher value than unrated ones?
SELECT CASE WHEN is_rated = 1 THEN 'Rated' ELSE 'Not Rated' END AS review_status,
COUNT(*) AS orders,
ROUND(AVG(cost_of_the_order), 2) AS avg_order_value,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins
FROM food_orders
GROUP BY is_rated;

-- 4.3 Cuisines with fastest average delivery
SELECT cuisine_type,
ROUND(AVG(delivery_time), 1) AS avg_delivery_mins,
COUNT(*) AS orders
FROM food_orders
GROUP BY cuisine_type
HAVING orders >= 20
ORDER BY avg_delivery_mins ASC
LIMIT 10;

-- 4.4 High-value orders (top 10%) by cuisine
SELECT cuisine_type,
COUNT(*) AS premium_orders,
ROUND(AVG(cost_of_the_order), 2) AS avg_value
FROM food_orders
WHERE cost_of_the_order > (
SELECT ROUND(AVG(cost_of_the_order) + STDDEV(cost_of_the_order), 2)
FROM food_orders
)
GROUP BY cuisine_type
ORDER BY premium_orders DESC;
