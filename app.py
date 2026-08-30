import streamlit as st
import pandas as pd
import joblib
import plotly.express as px

# Setup Page UI
st.set_page_config(page_title="RTO-Guard AI", page_icon="🛡️", layout="wide")

# Custom CSS for polish
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1E3A8A; margin-bottom: 0px; }
    .sub-header { font-size: 1.2rem; color: #64748B; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🛡️ RTO-Guard: Predictive Returns AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload today\'s unfulfilled Shopify orders. Prevent margin bleed by catching COD fraud before shipping.</p>', unsafe_allow_html=True)

# Load Model
@st.cache_resource
def load_model():
    return joblib.load('rto_model.pkl')
try:
    model = load_model()
except Exception as e:
    st.error(f"Cannot load model: {e}")

# Sidebar inputs
with st.sidebar:
    st.header("⚙️ Engine Settings")
    avg_shipping_cost = st.number_input("Est. Shipping Cost (Forward+Return) ₹", value=150)
    risk_threshold = st.slider("RTO Risk Threshold (%)", min_value=50, max_value=99, value=75, help="Orders above this score are flagged.")
    st.divider()
    uploaded_file = st.file_uploader("Upload 'real_unfulfilled_orders.csv'", type="csv")

# Explainer function
def get_risk_reason(row):
    reasons = []
    if row.get('is_cod', 0) == 1: reasons.append("COD")
    if row.get('is_guest', 0) == 1: reasons.append("Guest")
    if row.get('hour_of_day', 12) <= 5 or row.get('hour_of_day', 12) >= 23: reasons.append("Late Night")
    if row.get('cart_value', 0) > 3000: reasons.append("High Value")
    return " + ".join(reasons) if reasons else "Pattern Anomaly"

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Predict
    features = df[['is_cod', 'is_guest', 'cart_value', 'hour_of_day']]
    df['RTO_Probability'] = (model.predict_proba(features)[:, 1] * 100).round(1)
    high_risk_orders = df[df['RTO_Probability'] >= risk_threshold].copy()
    safe_orders = df[df['RTO_Probability'] < risk_threshold].copy()
    
    # --- UI TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "🚨 Actionable Flags", "🧠 How AI Works"])
    
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Orders", len(df))
        col2.metric("Safe to Ship", len(safe_orders), delta_color="normal")
        col3.metric("High-Risk RTOs", len(high_risk_orders), delta="-"+str(len(high_risk_orders)), delta_color="inverse")
        money_saved = len(high_risk_orders) * avg_shipping_cost
        col4.metric("💰 Margins Saved", f"₹ {money_saved:,}", help="Saved by halting shipping constraints.")
        
        st.divider()
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Risk Distribution")
            pie_data = pd.DataFrame({'Category': ['Safe Orders', 'High Risk'], 'Count': [len(safe_orders), len(high_risk_orders)]})
            fig1 = px.pie(pie_data, values='Count', names='Category', hole=0.4, color='Category', color_discrete_map={'Safe Orders':'#22c55e', 'High Risk':'#ef4444'})
            st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            st.subheader("Fraud by Time of Day")
            # Group by hour
            if len(high_risk_orders) > 0:
                fraud_by_hour = high_risk_orders.groupby('hour_of_day').size().reset_index(name='fraud_cases')
                fig2 = px.bar(fraud_by_hour, x='hour_of_day', y='fraud_cases', labels={'hour_of_day':'Hour (24h)', 'fraud_cases': 'Blocked Orders'}, color_discrete_sequence=['#f59e0b'])
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Not enough fraud data to chart.")

    with tab2:
        st.subheader("Actionable Quarantine List")
        if len(high_risk_orders) > 0:
            high_risk_orders['Risk Reason'] = high_risk_orders.apply(get_risk_reason, axis=1)
            display_df = high_risk_orders[['order_id', 'Risk Reason', 'RTO_Probability', 'cart_value']].sort_values('RTO_Probability', ascending=False)
            
            # Export logic
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Quarantine List for Warehouse", data=csv, file_name="quarantined_orders.csv", mime="text/csv", type='primary')
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.dataframe(display_df, use_container_width=True, column_config={
                "order_id": "Order ID", "Risk Reason": "🚨 Flagged Reason",
                "cart_value": st.column_config.NumberColumn("Cart Value", format="₹%d"),
                "RTO_Probability": st.column_config.ProgressColumn("Risk Score", format="%f%%", min_value=0, max_value=100)
            }, hide_index=True)
        else:
            st.success("No risky orders detected.")

    with tab3:
        st.markdown("### Model Architecture")
        st.info("This Random Forest model analyzes multi-variate statistical logic. Simple rule-based systems fail because they block *all* COD orders. This engine uses Machine Learning to only block COD if combined with anomalous geometries (like 3 AM checkouts with inflated cart values).")
        # Feature importance
        st.markdown("""
        **Key Predictive Features used by algorithm:**
        1. **Payment Type (COD):** The strongest historical indicator for Return-to-Origin.
        2. **Checkout Hour:** Anomalous spikes between 1:00 AM - 4:00 AM.
        3. **Account Status:** Guest checkouts block verification tracking.
        """)
else:
    st.info("👈 Please enter the dashboard by uploading yesterday's CSV data on the left.")
