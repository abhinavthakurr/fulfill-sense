import pandas as pd
import numpy as np

n = 150
pincodes = [560034, 110001, 400001, 600001, 700001, 411001, 302001]
cities = ['Bangalore', 'New Delhi', 'Mumbai', 'Chennai', 'Kolkata', 'Pune', 'Jaipur']
city_map = dict(zip(pincodes, cities))

np.random.seed(42)
is_cod = np.random.choice([0, 1], p=[0.3, 0.7], size=n) # High COD rate for India
is_guest = np.random.choice([0, 1], p=[0.6, 0.4], size=n)
cart_values = np.random.randint(499, 12999, size=n)
hours = np.random.randint(0, 24, size=n)
pincode_col = np.random.choice(pincodes, size=n)

df = pd.DataFrame({
    'order_id': ['ORD-2026-' + str(i) for i in range(9000, 9000+n)],
    'city': [city_map[p] for p in pincode_col],
    'pincode': pincode_col,
    'is_cod': is_cod,
    'is_guest': is_guest,
    'cart_value': cart_values,
    'hour_of_day': hours
})
df.to_csv('real_unfulfilled_orders.csv', index=False)
print("Successfully created 'real_unfulfilled_orders.csv'")
