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

uploaded_file = st.file_uploader("Upload 'real_unfulfilled_orders.csv'", type="csv")

# Explainer function for the PM requirement
def get_risk_reason(row):
    reasons = []
    if row['is_cod'] == 1: reasons.append("Cash On Delivery")
    if row['is_guest'] == 1: reasons.append("Guest Account")
    if row['hour_of_day'] <= 5 or row['hour_of_day'] >= 23: reasons.append("Late Night Order")
    if row['cart_value'] > 3000: reasons.append("High Cart Value")
    
    if len(reasons) == 0: return "Unknown Statistical Pattern"
    return " + ".join(reasons)

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
    col3.metric("🚨 Potential Cash Saved", f"₹ {money_saved:,}", help="If you cancel or mandate OTP for these orders.")

    # --- UI DISPLAY ---
    st.divider()
    if len(high_risk_orders) > 0:
        st.error(f"⚠️ We found {len(high_risk_orders)} orders with a high probability of being returned/fake.")
        
        # 1. Apply the PM requirement (Risk Reason)
        high_risk_orders['Risk Reason'] = high_risk_orders.apply(get_risk_reason, axis=1)
        
        display_df = high_risk_orders[['order_id', 'Risk Reason', 'RTO_Probability', 'cart_value']].sort_values('RTO_Probability', ascending=False)
        
        # 2. Fix the crash by using Streamlit's beautiful native styling instead of buggy Pandas styling
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "order_id": "Order ID",
                "Risk Reason": "🚨 Why is this risky?",
                "cart_value": st.column_config.NumberColumn("Cart Value", format="₹%d"),
                "RTO_Probability": st.column_config.ProgressColumn(
                    "Risk Score (%)",
                    help="Statistical probability of this order bouncing",
                    format="%f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
            hide_index=True
        )
    else:
        st.success("✅ All clear! Your current batch of orders looks mathematically healthy.")
else:
    st.info("👈 Please upload your unfulfilled orders CSV to begin.")
