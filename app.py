import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title='Food Delivery Analytics',
    page_icon='🍕',
    layout='wide'
)


# ── LOAD DATA ──
@st.cache_data
def load_data():
    orders = pd.read_csv('clean_food_orders.csv')
    perf   = pd.read_csv('restaurant_performance.csv')
    return orders, perf

# Handle missing CSV files gracefully
if not os.path.exists('clean_food_orders.csv'):
    st.error('clean_food_orders.csv not found. Run data_prep.py first!')
    st.code('python3 data_prep.py')
    st.stop()

orders, perf = load_data()


# ── HEADER ──
st.title('🍕 Food Delivery Analytics Hub')
st.markdown('Restaurant performance · Delivery efficiency · Customer insights')
st.divider()


# ── SIDEBAR FILTERS ──
st.sidebar.header('🔧 Filters')

all_cuisines = sorted(orders['cuisine_type'].dropna().unique().tolist())
sel_cuisine  = st.sidebar.selectbox('Cuisine Type', ['All'] + all_cuisines)
sel_day      = st.sidebar.radio('Day Type', ['All', 'Weekday', 'Weekend'])

min_rating = st.sidebar.slider('Minimum Rating', 1.0, 5.0, 1.0, 0.5)

# Apply filters
filtered = orders.copy()
if sel_cuisine != 'All':
    filtered = filtered[filtered['cuisine_type'] == sel_cuisine]
if sel_day != 'All':
    filtered = filtered[filtered['day_of_the_week'] == sel_day]
filtered = filtered[filtered['rating'] >= min_rating]

# Handle empty filtered result
if len(filtered) == 0:
    st.warning('No data matches the selected filters. Try changing the filters.')
    st.stop()


# ── KPI CARDS ──
col1, col2, col3, col4 = st.columns(4)
col1.metric('Total Orders',      f"{len(filtered):,}")
col2.metric('Total Revenue',     f"USD {filtered['cost_of_the_order'].sum():,.0f}")
col3.metric('Avg Delivery Time', f"{filtered['delivery_time'].mean():.1f} min")
col4.metric('Avg Rating',        f"{filtered['rating'].mean():.2f} / 5")
st.divider()


# ── TABS ──
tab1, tab2, tab3 = st.tabs(['🍽️ Cuisines', '🏆 Restaurants', '⏱️ Delivery'])


# ── TAB 1: CUISINES ──
with tab1:
    st.subheader('Cuisine Performance')

    cuisine_stats = (
        filtered
        .groupby('cuisine_type')
        .agg(orders=('order_id','count'),
             revenue=('cost_of_the_order','sum'),
             rating=('rating','mean'))
        .reset_index()
        .sort_values('orders', ascending=False)
        .head(10)
    )

    fig1 = px.bar(
        cuisine_stats,
        x='cuisine_type', y='orders',
        color='rating',
        color_continuous_scale='RdYlGn',
        title='Top Cuisines by Orders (color = avg rating)',
        labels={'cuisine_type':'Cuisine','orders':'Total Orders','rating':'Avg Rating'}
    )
    fig1.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.scatter(
        cuisine_stats,
        x='orders', y='revenue',
        size='rating', color='rating',
        text='cuisine_type',
        color_continuous_scale='Plasma',
        title='Orders vs Revenue by Cuisine'
    )
    fig2.update_traces(textposition='top center')
    st.plotly_chart(fig2, use_container_width=True)


# ── TAB 2: RESTAURANTS ──
with tab2:
    st.subheader('Restaurant Leaderboard')

    min_orders = st.slider('Min Orders to qualify', 1, 30, 5)

    top_rest = (
        perf[perf['total_orders'] >= min_orders]
        .sort_values('perf_score', ascending=False)
        .head(15)
        .reset_index(drop=True)
    )

    if len(top_rest) == 0:
        st.warning('No restaurants meet the minimum order threshold.')
    else:
        fig3 = px.bar(
            top_rest,
            x='perf_score', y='restaurant_name',
            orientation='h',
            color='perf_score',
            color_continuous_scale='Pinkyl',
            title='Top Restaurants by Performance Score (0-100)',
            labels={'perf_score':'Score','restaurant_name':'Restaurant'}
        )
        fig3.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader('Leaderboard Table')
        display_cols = {
            'restaurant_name': 'Restaurant',
            'total_orders':    'Orders',
            'avg_rating':      'Avg Rating',
            'avg_del_time':    'Avg Delivery (min)',
            'avg_cost':        'Avg Cost (USD)',
            'perf_score':      'Score'
        }
        st.dataframe(
            top_rest[list(display_cols.keys())].rename(columns=display_cols),
            use_container_width=True
        )


# ── TAB 3: DELIVERY ──
with tab3:
    st.subheader('Delivery Time Analysis')

    fig4 = px.histogram(
        filtered,
        x='delivery_time',
        nbins=20,
        color='time_category',
        color_discrete_map={
            'Fast':   '#22c55e',
            'Normal': '#f59e0b',
            'Slow':   '#ef4444'
        },
        title='Delivery Time Distribution by Speed Category',
        labels={'delivery_time':'Delivery Time (mins)','time_category':'Speed'}
    )
    st.plotly_chart(fig4, use_container_width=True)

    day_comp = (
        filtered
        .groupby('day_of_the_week')
        .agg(avg_delivery=('delivery_time','mean'),
             avg_prep=('food_preparation_time','mean'))
        .reset_index()
    )

    fig5 = px.bar(
        day_comp,
        x='day_of_the_week',
        y=['avg_delivery', 'avg_prep'],
        barmode='group',
        title='Avg Delivery vs Prep Time: Weekday vs Weekend',
        labels={'value':'Minutes','variable':'Time Type','day_of_the_week':'Day'}
    )
    st.plotly_chart(fig5, use_container_width=True)

    # Speed breakdown summary
    st.subheader('Delivery Speed Breakdown')
    speed_summary = (
        filtered
        .groupby('time_category')
        .agg(orders=('order_id','count'),
             avg_rating=('rating','mean'),
             avg_cost=('cost_of_the_order','mean'))
        .reset_index()
        .sort_values('orders', ascending=False)
    )
    st.dataframe(speed_summary, use_container_width=True)


st.divider()
st.caption('Python + MySQL + Streamlit + Plotly')