
from license_manager import licenser
import os
import hashlib

# Force default salt if not present, to match what the app likely uses if no .env
if "LICENSE_SALT" not in os.environ:
    os.environ["LICENSE_SALT"] = "coca-cola-secret-recipe-2026"

machine_code = licenser.get_machine_code()
machine_id_raw = licenser.machine_id
email = "mirkotornani@gmail.com"
secret_salt = os.environ.get("LICENSE_SALT", "coca-cola-secret-recipe-2026")

expected_raw = f"{machine_id_raw}:{email}:{secret_salt}"
key = hashlib.sha256(expected_raw.encode()).hexdigest().upper()[:24]

print(f"Machine Code: {machine_code}")
print(f"Email: {email}")
print(f"Activation Key: {key}")
