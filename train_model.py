import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

print("Generating synthetic Indian e-commerce data...")
np.random.seed(42)
n_samples = 5000

# 1. Generate realistic features
is_cod = np.random.choice([0, 1], p=[0.4, 0.6], size=n_samples) # 60% COD
is_guest = np.random.choice([0, 1], p=[0.7, 0.3], size=n_samples) # 30% guest
cart_value = np.random.randint(300, 5000, size=n_samples)
hour_of_day = np.random.randint(0, 24, size=n_samples)

# 2. RTO Probability Logic (High risk if COD + Guest + Late Night/High Value)
rto_probability = (
    (is_cod * 0.4) + 
    (is_guest * 0.3) + 
    (np.where((hour_of_day >= 0) & (hour_of_day <= 5), 0.2, 0)) + 
    (np.where(cart_value > 3000, 0.1, 0))
)

# 3. Convert to 1 (RTO) or 0 (Delivered)
is_rto = np.where(rto_probability + np.random.normal(0, 0.1, n_samples) >= 0.7, 1, 0)

# 4. Create DataFrame & Train Model
df = pd.DataFrame({
    'is_cod': is_cod, 'is_guest': is_guest, 
    'cart_value': cart_value, 'hour_of_day': hour_of_day, 'is_rto': is_rto
})

X = df[['is_cod', 'is_guest', 'cart_value', 'hour_of_day']]
y = df['is_rto']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training Random Forest Classifier...")
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# 5. Save Model and Test Data
joblib.dump(model, 'rto_model.pkl')
print(f"Model saved successfully! Accuracy: {model.score(X_test, y_test):.2f}")

test_orders = df.sample(50).drop('is_rto', axis=1).reset_index().rename(columns={'index': 'order_id'})
test_orders.to_csv('todays_unfulfilled_orders.csv', index=False)
print("Saved sample CSV for the dashboard.")
