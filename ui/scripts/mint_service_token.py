from datetime import datetime, timedelta

from data.crud import create_service_token
from data.models import User

service_user = User.find_one(User.role == "service").run()
if not service_user:
    raise RuntimeError("Service user not found")

token = create_service_token(service_user)

print("SERVICE TOKEN (store securely):")
print(token)
print("Expires:", datetime.utcnow() + timedelta(days=30))
