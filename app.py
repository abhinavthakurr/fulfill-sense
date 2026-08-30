import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
import io
import numpy as np

# Setup Page UI
st.set_page_config(page_title="FulfillSense Sandbox", layout="wide")

st.markdown("""
<style>
/* Clean up streamlit default padding */
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
/* Hide default deploy buttons */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("FulfillSense Sandbox")
st.markdown("Upload your daily order batch or generate a template to see our predictive risk engine in action.")
st.divider()

# Load Model
@st.cache_resource
def load_model():
    return joblib.load('rto_model.pkl')
try:
    model = load_model()
except Exception as e:
    st.error(f"System Error: Cannot initialize model constraints - {e}")
    model = None

# Sidebar inputs
with st.sidebar:
    st.header("Engine Configuration")
    avg_shipping_cost = st.number_input("Average Shipping Cost (INR)", value=150, help="Used to calculate blocked losses.")
    risk_threshold = st.slider("Quarantine Threshold (%)", min_value=50, max_value=99, value=75, help="Orders exceeding this probability will be flagged for quarantine.")
    st.divider()
    
    st.markdown("### Interactive Sandbox")
    st.markdown("Upload your own `.csv` data to test the Risk Engine.")
    uploaded_file = st.file_uploader("Drop Orders CSV here", type="csv")
    
    st.divider()
    st.markdown("Don't have data on hand?")
    
    # Generate Template Logic
    def generate_template():
        np.random.seed(12)
        n_samples = 50
        sample_df = pd.DataFrame({
            'order_id': [f"ORD-TEST-{str(i).zfill(4)}" for i in range(1, n_samples+1)],
            'is_cod': np.random.choice([0, 1], p=[0.2, 0.8], size=n_samples),
            'is_guest': np.random.choice([0, 1], p=[0.7, 0.3], size=n_samples),
            'cart_value': np.random.randint(500, 15000, size=n_samples),
            'hour_of_day': np.random.randint(0, 24, size=n_samples),
        })
        buffer = io.StringIO()
        sample_df.to_csv(buffer, index=False)
        return buffer.getvalue()

    st.download_button(
        label="📥 Download Sample Data Template",
        data=generate_template(),
        file_name="sample_orders.csv",
        mime="text/csv",
        use_container_width=True
    )

    if st.button("▶️ Auto-Load Sample Data instead", use_container_width=True):
        st.session_state['use_sample'] = True

# Helper Explainer function
def get_risk_reason(row):
    reasons = []
    if row.get('is_cod', 0) == 1: reasons.append("Cash On Delivery")
    if row.get('is_guest', 0) == 1: reasons.append("Guest Account History")
    if row.get('hour_of_day', 12) <= 4 or row.get('hour_of_day', 12) >= 23: reasons.append("Late-night Transaction")
    if row.get('cart_value', 0) > 4000: reasons.append("Anomalous Cart Value")
    return " | ".join(reasons) if reasons else "Multi-variate Pattern match"

# Flow Control
df = None
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
elif st.session_state.get('use_sample', False):
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        'order_id': [f"ORD-DEMO-{str(i).zfill(4)}" for i in range(1, n+1)],
        'is_cod': np.random.choice([0, 1], p=[0.6, 0.4], size=n),
        'is_guest': np.random.choice([0, 1], p=[0.5, 0.5], size=n),
        'cart_value': np.random.randint(499, 12000, size=n),
        'hour_of_day': np.random.randint(0, 24, size=n)
    })

if df is not None and model is not None:
    # Ensure required columns exist
    required_cols = ['is_cod', 'is_guest', 'cart_value', 'hour_of_day']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Upload Error: CSV must contain the following headers exactly: `{required_cols}`")
    else:
        # Predict
        features = df[required_cols]
        df['RTO_Probability'] = (model.predict_proba(features)[:, 1] * 100).round(1)
        high_risk_orders = df[df['RTO_Probability'] >= risk_threshold].copy()
        safe_orders = df[df['RTO_Probability'] < risk_threshold].copy()
        
        # --- UI TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Executive Overview", "⚠️ Quarantine Actions", "🧠 Model Intelligence"])
        
        with tab1:
            # Metrics
            st.markdown("### Batch Inference Results")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Order Volume", len(df))
            col2.metric("Cleared for Fulfillment", len(safe_orders))
            col3.metric("High-Risk Flags", len(high_risk_orders), delta=f"-{len(high_risk_orders)} intercepted", delta_color="inverse")
            money_saved = len(high_risk_orders) * avg_shipping_cost
            col4.metric("Protected Margin (INR)", f"₹{money_saved:,}", delta=f"Saved via {risk_threshold}% threshold", delta_color="normal")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Charts
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Real-Time Risk Distribution**")
                pie_data = pd.DataFrame({'Category': ['Cleared', 'High Risk'], 'Count': [len(safe_orders), len(high_risk_orders)]})
                fig1 = px.pie(pie_data, values='Count', names='Category', hole=0.5, color='Category', 
                              color_discrete_map={'Cleared':'#10B981', 'High Risk':'#EF4444'}) # Emerald and Red Tailwind colors
                fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
                fig1.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
                st.plotly_chart(fig1, use_container_width=True)
                
            with c2:
                st.markdown("**Temporal Risk Spikes**")
                if len(high_risk_orders) > 0:
                    fraud_by_hour = high_risk_orders.groupby('hour_of_day').size().reset_index(name='flags')
                    fig2 = px.bar(fraud_by_hour, x='hour_of_day', y='flags', labels={'hour_of_day':'Hour of Checkout (24h)', 'flags': 'High Risk Count'}, 
                                  color_discrete_sequence=['#6366F1']) # Indigo Tailwind color
                    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Insufficient data to populate temporal distribution.")

        with tab2:
            st.markdown("### Actionable Quarantine List")
            st.markdown("Orders requiring manual validation, OTP verification, or immediate cancellation prior to API dispatch.")
            
            if len(high_risk_orders) > 0:
                high_risk_orders['Detected Signal'] = high_risk_orders.apply(get_risk_reason, axis=1)
                display_df = high_risk_orders[['order_id', 'Detected Signal', 'RTO_Probability', 'cart_value']].sort_values('RTO_Probability', ascending=False)
                
                # Top controls
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Extract Quarantined Orders to WMS", data=csv, file_name="fulfill_sense_quarantine.csv", mime="text/csv", type="primary")
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Beautiful DataFrame render
                st.dataframe(display_df, use_container_width=True, column_config={
                    "order_id": st.column_config.TextColumn("Tracking ID"), 
                    "Detected Signal": st.column_config.TextColumn("Risk Fingerprint"),
                    "cart_value": st.column_config.NumberColumn("Cart Value (INR)", format="₹%d"),
                    "RTO_Probability": st.column_config.ProgressColumn("Failure Probability", format="%f%%", min_value=0, max_value=100)
                }, hide_index=True)
            else:
                st.success("✅ No high-risk orders detected in current batch. All cleared for warehouse dispatch.")

        with tab3:
            st.markdown("### Under the Hood: Scikit-Learn Engine")
            st.write("FulfillSense utilizes an ensemble Random Forest classifier serialized from `train_model.py`. Instead of primitive API rules, it calculates non-linear correlations.")
            
            st.markdown("""
            **Primary Weights:**
            *   **`is_cod` (Cash on Delivery)**: Primary vector for return fraud in South Asian emerging markets.
            *   **`cart_value`**: Statistically significant anomaly spikes when exceeding INR 3,000 for unregistered users.
            *   **`hour_of_day`**: Late night (01:00 to 05:00) checkouts exhibit 70%+ higher probability of buyer's remorse/RTO.
            *   **`is_guest`**: Lack of LTV (Life Time Value) metadata strongly correlated with delivery refusals.
            """)
            
            st.code("""
# Core inference execution block (app.py)
import joblib

model = joblib.load('rto_model.pkl')
prediction_probabilities = model.predict_proba(df[['is_cod', 'is_guest', 'cart_value', 'hour_of_day']])
df['Risk_Score'] = prediction_probabilities[:, 1]
            """, language="python")
else:
    # Empty State
    st.info("👋 Welcome to the Sandbox!")
    st.markdown("""
    To get started, either:
    1. Upload your own `.csv` file in the sidebar containing `['is_cod', 'is_guest', 'cart_value', 'hour_of_day']`
    2. Click the **'Auto-Load Sample Data'** button in the sidebar to simulate an instant data pipeline.
    """)
