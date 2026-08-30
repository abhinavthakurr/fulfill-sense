import streamlit as st
import pandas as pd
import joblib

# Setup Page UI
st.set_page_config(page_title="RTO-Guard UI", layout="wide")
st.title("🛡️ RTO-Guard: Predictive Fraud Engine")
st.markdown("Upload today's unfulfilled Shopify orders. Our statistical engine will flag high-risk COD orders *before* you pay to ship them.")

# Load the Stats Model
@st.cache_resource
def load_model():
    return joblib.load('rto_model.pkl')

model = load_model()

# Sidebar for merchant inputs
st.sidebar.header("Merchant Settings")
avg_shipping_cost = st.sidebar.number_input("Average Shipping Cost (Forward + Return) in ₹", value=150)
risk_threshold = st.sidebar.slider("RTO Risk Threshold (%)", min_value=50, max_value=99, value=75)

uploaded_file = st.file_uploader("Upload 'todays_unfulfilled_orders.csv'", type="csv")

if uploaded_file is not None:
    # Read the data
    df = pd.read_csv(uploaded_file)
    
    # Run the Statistical Prediction
    features = df[['is_cod', 'is_guest', 'cart_value', 'hour_of_day']]
    probabilities = model.predict_proba(features)[:, 1] 
    
    df['RTO_Probability'] = (probabilities * 100).round(1)
    
    # Filter High Risk Orders
    high_risk_orders = df[df['RTO_Probability'] >= risk_threshold].copy()
    
    # --- BUSINESS IMPACT METRICS ---
    st.divider()
    st.subheader("📊 Business Impact Analysis")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders Analyzed", len(df))
    col2.metric("High-Risk RTOs Flagged", len(high_risk_orders), delta_color="inverse")
    
    # Calculate Money Saved
    money_saved = len(high_risk_orders) * avg_shipping_cost
    col3.metric("🚨 Potential Cash Saved", f"₹ {money_saved:,}", help="If you cancel these orders.")

    # --- UI DISPLAY ---
    st.divider()
    if len(high_risk_orders) > 0:
        st.error(f"⚠️ We found {len(high_risk_orders)} orders with a high probability of being returned/fake.")
        
        display_df = high_risk_orders[['order_id', 'cart_value', 'RTO_Probability', 'is_cod', 'is_guest']].sort_values('RTO_Probability', ascending=False)
        st.dataframe(display_df.style.background_gradient(subset=['RTO_Probability'], cmap='Reds'), use_container_width=True)
    else:
        st.success("✅ All clear! Your current batch of orders looks mathematically healthy.")
else:
    st.info("👈 Please upload your unfulfilled orders CSV to begin.")
