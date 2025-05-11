import jwt
import datetime

JWT_SECRET = "supersecret"  # The same secret used in your FastAPI app
expiration = datetime.datetime.utcnow() + datetime.timedelta(days=2)  # Token expiration time

# Create the token with payload and expiration
payload = {
    "sub": "test_user",  # Add any claims you need, like the username or user id
    "exp": expiration
}

# Generate the JWT token
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
print(token)  # Copy this token for use in Swagger UI
