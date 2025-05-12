import requests

BASE_URL = "http://localhost:8000"  # Change to your server URL

# Sample user credentials
USER = {
    "username": "testuser1",
    "email": "testuser1@example.com",
    "password": "securepassword"
}

# Register the user
def register_user():
    url = f"{BASE_URL}/auth/register"
    response = requests.post(url, json=USER)
    print("Register:", response.status_code, response.json())
    return response.ok

# Login and get token
def login_user():
    url = f"{BASE_URL}/auth/token"
    data = {
        "username": USER["email"],
        "password": USER["password"]
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    print("Login:", response.status_code, response.json())
    # import pdb; pdb.set_trace()
    return response.json()["access_token"]

# Create a playlist
def create_playlist(token, name="My Playlist"):
    url = f"{BASE_URL}/playlists"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "name": name,
        "owner_type": "user"
    }
    response = requests.post(url, json=data, headers=headers)
    print("Create Playlist:", response.status_code, response.json())
    return name

# Create a team
def create_team(token, name="My Team"):
    url = f"{BASE_URL}/teams"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "name": name
    }
    response = requests.post(url, json=data, headers=headers)
    print("Create Team:", response.status_code, response.json())
    return response.json()["id"]

# Assign the playlist to the team
def assign_playlist_to_team(token, playlist_name, team_id):
    url = f"{BASE_URL}/playlists/{playlist_name}/assign-team"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"team_id": team_id}
    response = requests.put(url, headers=headers, params=params)
    print("Assign Playlist:", response.status_code, response.json())

def main():
    if register_user():
        token = login_user()
        team_id = create_team(token)
        playlist_name = create_playlist(token)
        assign_playlist_to_team(token, playlist_name, team_id)

if __name__ == "__main__":
    main()
