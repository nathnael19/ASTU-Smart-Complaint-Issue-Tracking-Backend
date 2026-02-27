from app.core.supabase import supabase_client
import sys
import time

email = "nathnaelnigussie19@astu.edu.et"
password = "TestPassword123!"

try:
    print(f"--- Testing Supabase sign_up for: '{email}' ---")
    # Using the exact same structure as in auth.py
    res = supabase_client.auth.sign_up(
        credentials={"email": email, "password": password}
    )
    print("SUCCESS")
    print("Response User:", res.user)
except Exception as e:
    print("\n--- ERROR CAUGHT ---")
    print(f"Message: {str(e)}")
    print(f"Type: {type(e)}")
    if hasattr(e, 'status'):
        print(f"Status: {e.status}")
    if hasattr(e, 'code'):
        print(f"Code: {e.code}")
    
    # Try with keyword arguments instead of credentials dict to see if it makes a difference
    print("\n--- Testing alternative: sign_up(email=email, password=password) ---")
    try:
        res2 = supabase_client.auth.sign_up(email=email, password=password)
        print("SUCCESS with kwarg format")
    except Exception as e2:
         print(f"Alternative also failed: {str(e2)}")
