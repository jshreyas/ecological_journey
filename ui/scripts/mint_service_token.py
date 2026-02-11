from ui.data.crud import create_service_token
from ui.data.models import User

service_user = User.find_one(User.role == "service").run()
if not service_user:
    raise RuntimeError("Service user not found")

token = create_service_token(service_user)

# write only – never print
with open("/tmp/service_token.txt", "w") as f:
    f.write(token)
