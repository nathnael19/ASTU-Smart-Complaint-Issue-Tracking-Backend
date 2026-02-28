import sys
import os
import getpass
from dotenv import load_dotenv

# Add Backend root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir) if "scripts" in current_dir else current_dir

# Load .env file explicitly
env_path = os.path.join(backend_root, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

sys.path.append(backend_root)

try:
    from app.core.supabase import supabase_admin
    from app.models.enums import UserRole, UserStatus
except ImportError as e:
    print(f"Error: Could not import app modules ({e}).")
    sys.exit(1)

def create_admin():
    """
    Creates an admin user by taking interactive input from the terminal.
    """
    print("\n" + "="*40)
    print("🛡️  CREATE SYSTEM ADMINISTRATOR 🛡️")
    print("="*40 + "\n")

    # 1. Collect Input
    full_name = input("👤 Full Name: ").strip()
    email = input("📧 Email: ").strip().lower()
    password = getpass.getpass("🔑 Password: ").strip()
    confirm_password = getpass.getpass("🔑 Confirm Password: ").strip()

    if not full_name or not email or not password:
        print("\n❌ Error: All fields are required.")
        return

    if password != confirm_password:
        print("\n❌ Error: Passwords do not match.")
        return

    # 2. Preparation
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    try:
        # 3. Create user in Supabase Auth
        print(f"\n🚀 Creating authentication account for: {email}...")
        
        auth_response = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name}
        })
        
        if not auth_response.user:
            print("❌ Failed to create authentication account.")
            return
            
        user_id = auth_response.user.id
        print(f"✅ Auth account created (ID: {user_id})")

        # 4. Create profile in the 'users' table
        print(f"📝 Creating database profile for {full_name}...")
        user_data = {
            "id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": UserRole.ADMIN,
            "status": UserStatus.ACTIVE
        }
        
        supabase_admin.table("users").insert(user_data).execute()
        
        print("\n" + "="*40)
        print("🎉 ADMIN CREATED SUCCESSFULLY!")
        print("="*40)
        print(f"Email:    {email}")
        print(f"Name:     {full_name}")
        print(f"Role:     ADMIN")
        print("="*40 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled.")
        sys.exit(0)
