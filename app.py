import streamlit as st
import pandas as pd
import joblib
import plotly.express as px

# Setup Page UI
st.set_page_config(page_title="FulfillSense", layout="wide")

# Native Streamlit Title (clean, no HTML hacks that break dark mode)
st.title("FulfillSense: Predictive Returns Intelligence")
st.markdown("Automated RTO risk assessment for unfulfilled e-commerce orders.")
st.divider()

# Load Model
@st.cache_resource
def load_model():
    return joblib.load('rto_model.pkl')
try:
    model = load_model()
except Exception as e:
    st.error(f"System Error: Cannot initialize model constraints - {e}")

# Sidebar inputs
with st.sidebar:
    st.header("Configuration")
    avg_shipping_cost = st.number_input("Average Shipping Cost (INR)", value=150)
    risk_threshold = st.slider("Risk Threshold (%)", min_value=50, max_value=99, value=75, help="Orders exceeding this probability will be flagged for quarantine.")
    st.divider()
    uploaded_file = st.file_uploader("Upload Orders CSV", type="csv")

# Explainer function
def get_risk_reason(row):
    reasons = []
    if row.get('is_cod', 0) == 1: reasons.append("Cash On Delivery")
    if row.get('is_guest', 0) == 1: reasons.append("Guest Account")
    if row.get('hour_of_day', 12) <= 5 or row.get('hour_of_day', 12) >= 23: reasons.append("Late-night Transaction")
    if row.get('cart_value', 0) > 3000: reasons.append("High Cart Value")
    return " | ".join(reasons) if reasons else "Anomalous Pattern"

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Predict
    features = df[['is_cod', 'is_guest', 'cart_value', 'hour_of_day']]
    df['RTO_Probability'] = (model.predict_proba(features)[:, 1] * 100).round(1)
    high_risk_orders = df[df['RTO_Probability'] >= risk_threshold].copy()
    safe_orders = df[df['RTO_Probability'] < risk_threshold].copy()
    
    # --- UI TABS ---
    tab1, tab2, tab3 = st.tabs(["Executive Overview", "Quarantine Details", "Model Architecture"])
    
    with tab1:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Order Volume", len(df))
        col2.metric("Cleared for Fulfillment", len(safe_orders))
        col3.metric("High-Risk Flags", len(high_risk_orders), delta="-"+str(len(high_risk_orders)), delta_color="inverse")
        money_saved = len(high_risk_orders) * avg_shipping_cost
        col4.metric("Protected Margin (INR)", f"₹{money_saved:,}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Risk Distribution**")
            pie_data = pd.DataFrame({'Category': ['Cleared', 'High Risk'], 'Count': [len(safe_orders), len(high_risk_orders)]})
            fig1 = px.pie(pie_data, values='Count', names='Category', hole=0.5, color='Category', 
                          color_discrete_map={'Cleared':'#64748B', 'High Risk':'#B91C1C'})
            fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            st.markdown("**High-Risk Flag Frequency by Checkout Hour**")
            if len(high_risk_orders) > 0:
                fraud_by_hour = high_risk_orders.groupby('hour_of_day').size().reset_index(name='flags')
                fig2 = px.bar(fraud_by_hour, x='hour_of_day', y='flags', labels={'hour_of_day':'Hour (24h format)', 'flags': 'Flag Count'}, 
                              color_discrete_sequence=['#475569'])
                fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Insufficient data to populate temporal distribution.")

    with tab2:
        st.markdown("**Actionable Quarantine List**")
        st.markdown("Orders requiring manual validation or OTP verification before dispatch.")
        
        if len(high_risk_orders) > 0:
            high_risk_orders['Pattern Flags'] = high_risk_orders.apply(get_risk_reason, axis=1)
            display_df = high_risk_orders[['order_id', 'Pattern Flags', 'RTO_Probability', 'cart_value']].sort_values('RTO_Probability', ascending=False)
            
            # Export logic
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Quarantine CSV", data=csv, file_name="fulfill_sense_quarantine.csv", mime="text/csv")
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.dataframe(display_df, use_container_width=True, column_config={
                "order_id": "Order Identifier", 
                "Pattern Flags": "Detected Risk Factors",
                "cart_value": st.column_config.NumberColumn("Cart Value (INR)", format="₹%d"),
                "RTO_Probability": st.column_config.ProgressColumn("Risk Probability", format="%f%%", min_value=0, max_value=100)
            }, hide_index=True)
        else:
            st.success("No high-risk orders detected in current batch.")

    with tab3:
        st.markdown("**Model Intelligence & Feature Weights**")
        st.write("FulfillSense utilizes a Random Forest classification algorithm to detect multi-variate statistical anomalies that simple rule-based engines miss.")
        
        st.markdown("""
        **Primary Heuristics:**
        *   **Payment Typology:** High correlation between Cash-on-Delivery (COD) and return likelihood.
        *   **Temporal Anomalies:** Checkout timestamps cross-referenced against standard consumer behavior (e.g., 01:00 - 04:00 spikes).
        *   **Account Maturity:** Elevated risk in guest checkouts lacking historical Lifetime Value (LTV) data.
        """)
else:
    st.info("Awaiting input: Please upload the fulfillment batch CSV in the configuration panel.")
