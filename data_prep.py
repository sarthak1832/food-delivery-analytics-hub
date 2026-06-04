import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os, warnings
warnings.filterwarnings('ignore')
os.makedirs('visuals', exist_ok=True)

# Load credentials from .env file
load_dotenv()

# STEP 1 — LOAD DATA

print('Loading data...')
df = pd.read_csv('food_order.csv')
print('Shape:', df.shape)
print(df.head(3))
print('\nColumn types:')
print(df.dtypes)
print('\nMissing values:')
print(df.isnull().sum())

# STEP 2 — CLEAN DATA
print('\nCleaning data...')

# Fix rating: replace 'Not given' text with NaN
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

# Fill missing ratings with median
median_rating = df['rating'].median()
df['rating'] = df['rating'].fillna(median_rating)

# Strip whitespace from all text columns
for col in ['cuisine_type', 'restaurant_name', 'day_of_the_week']:
    df[col] = df[col].str.strip()

# Drop any remaining nulls in critical columns
df.dropna(subset=['order_id', 'cost_of_the_order', 'delivery_time'], inplace=True)

# Remove duplicates
before = len(df)
df.drop_duplicates(inplace=True)
print(f'Removed {before - len(df)} duplicate rows')
print('Clean shape:', df.shape)

# STEP 3 — FEATURE ENGINEERING
print('\nEngineering features...')

# Total time = prep + delivery
df['total_time'] = df['food_preparation_time'] + df['delivery_time']

# Delivery speed category
def time_cat(mins):
    if mins <= 25:   return 'Fast'
    elif mins <= 40: return 'Normal'
    else:            return 'Slow'

df['time_category'] = df['delivery_time'].apply(time_cat)

# Is rated flag
df['is_rated'] = df['rating'].notna().astype(int)

# ── RESTAURANT PERFORMANCE SCORE (0-100) ──
rest = df.groupby('restaurant_name').agg(
    avg_rating   = ('rating', 'mean'),
    avg_del_time = ('delivery_time', 'mean'),
    total_orders = ('order_id', 'count'),
    avg_cost     = ('cost_of_the_order', 'mean')
).reset_index()

def normalize(series):
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - series.min()) / rng

rest['perf_score'] = (
    normalize(rest['avg_rating'])     * 40 +
    normalize(-rest['avg_del_time'])  * 35 +
    normalize(rest['total_orders'])   * 25
).round(1)

print('Top 5 restaurants by performance:')
print(rest.nlargest(5, 'perf_score')[['restaurant_name', 'perf_score']])

# STEP 4 — EDA CHARTS

print('\nGenerating charts...')

# Chart 1: Top 10 cuisines by orders
plt.figure(figsize=(9, 5))
cuisine_counts = df['cuisine_type'].value_counts().head(10)
sns.barplot(x=cuisine_counts.values, y=cuisine_counts.index,
            palette='magma_r')
plt.title('Top 10 Cuisines by Number of Orders', fontweight='bold')
plt.xlabel('Orders')
plt.tight_layout()
plt.savefig('visuals/top_cuisines.png', dpi=150)
plt.close()
print('  Chart 1/4 saved')

# Chart 2: Weekday vs Weekend
day_stats = df.groupby('day_of_the_week').agg(
    orders  = ('order_id', 'count'),
    revenue = ('cost_of_the_order', 'sum')
).reset_index()
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
colors = ['#f472b6', '#e879f9']
axes[0].bar(day_stats['day_of_the_week'], day_stats['orders'], color=colors)
axes[0].set_title('Orders: Weekday vs Weekend')
axes[1].bar(day_stats['day_of_the_week'], day_stats['revenue'], color=colors)
axes[1].set_title('Revenue: Weekday vs Weekend')
plt.tight_layout()
plt.savefig('visuals/weekday_weekend.png', dpi=150)
plt.close()
print('  Chart 2/4 saved')

# Chart 3: Delivery time histogram
plt.figure(figsize=(8, 4))
sns.histplot(df['delivery_time'], bins=20, kde=True, color='#f472b6')
mean_val = df['delivery_time'].mean()
plt.axvline(mean_val, color='red', linestyle='--',
            label=f'Mean: {mean_val:.1f} min')
plt.title('Delivery Time Distribution')
plt.xlabel('Delivery Time (mins)')
plt.legend()
plt.tight_layout()
plt.savefig('visuals/delivery_dist.png', dpi=150)
plt.close()
print('  Chart 3/4 saved')

# Chart 4: Performance score scatter
plt.figure(figsize=(8, 5))
sc = plt.scatter(
    rest['avg_rating'], rest['perf_score'],
    alpha=0.6, c=rest['total_orders'],
    cmap='plasma', s=80, edgecolors='black', linewidth=0.3
)
plt.colorbar(sc, label='Total Orders')
plt.title('Performance Score vs Avg Rating')
plt.xlabel('Avg Rating')
plt.ylabel('Performance Score')
plt.tight_layout()
plt.savefig('visuals/perf_vs_rating.png', dpi=150)
plt.close()
print('  Chart 4/4 saved')

# STEP 5 — EXPORT CLEAN CSVs (used by app.py)

df.to_csv('clean_food_orders.csv', index=False)
rest.to_csv('restaurant_performance.csv', index=False)
print('\nCSVs exported: clean_food_orders.csv, restaurant_performance.csv')

# Fix NaN → None so MySQL reads them as NULL
df   = df.where(pd.notnull(df), None)
rest = rest.where(pd.notnull(rest), None)

# STEP 6 — LOAD INTO MYSQL

print('\nConnecting to MySQL...')

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )

    if not conn.is_connected():
        raise Error('Connection failed')

    print('Connected to MySQL!')
    cursor = conn.cursor()

    # ── food_orders table ──
    cursor.execute('DROP TABLE IF EXISTS food_orders;')
    cursor.execute('''
        CREATE TABLE food_orders (
            order_id INT,
            customer_id INT,
            restaurant_name VARCHAR(100),
            cuisine_type  VARCHAR(50),
            cost_of_the_order FLOAT,
            day_of_the_week  VARCHAR(20),
            rating FLOAT,
            food_preparation_time INT,
            delivery_time INT,
            total_time INT,
            time_category VARCHAR(10),
            is_rated INT
        );
    ''')

    food_rows = [
        (int(r.order_id), int(r.customer_id), str(r.restaurant_name),
         str(r.cuisine_type), float(r.cost_of_the_order), str(r.day_of_the_week),
         float(r.rating), int(r.food_preparation_time), int(r.delivery_time),
         int(r.total_time), str(r.time_category), int(r.is_rated))
        for r in df.itertuples(index=False)
    ]
    batch = 500
    for i in range(0, len(food_rows), batch):
        cursor.executemany(
            'INSERT INTO food_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            food_rows[i:i+batch]
        )
    conn.commit()
    print(f'food_orders loaded: {len(food_rows)} rows')

    # ── restaurant_perf table ──
    cursor.execute('DROP TABLE IF EXISTS restaurant_perf;')
    cursor.execute('''
        CREATE TABLE restaurant_perf (
            restaurant_name  VARCHAR(100),
            avg_rating FLOAT,
            avg_del_time FLOAT,
            total_orders INT,
            avg_cost FLOAT,
            perf_score FLOAT
        );
    ''')

    cols = ['restaurant_name','avg_rating','avg_del_time',
            'total_orders','avg_cost','perf_score']
    rest_rows = [tuple(r) for r in rest[cols].itertuples(index=False)]
    cursor.executemany(
        'INSERT INTO restaurant_perf VALUES (%s,%s,%s,%s,%s,%s)',
        rest_rows
    )
    conn.commit()
    print(f'restaurant_perf loaded: {len(rest_rows)} rows')

    print('\nAll done! MySQL loaded successfully.')

except Error as e:
    print(f'MySQL Error: {e}')
    print('Check: is MySQL running? brew services start mysql')
    print('Check: is your .env file correct?')

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print('MySQL connection closed.')