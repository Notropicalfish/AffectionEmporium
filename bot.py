# This is a serverless function, for example, at /api/send_message.py
# You would deploy this on a platform like Vercel.

import os
import json
import httpx # An asynchronous HTTP client, like 'requests'

# --- CONFIGURATION ---
# These are read from your Vercel Environment Variables
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_API_BASE_URL = "https://discord.com/api/v10"

# Set up the authorization headers for all API requests
headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

# This is the main function Vercel will run
# Note: Vercel's Python runtime requires a specific handler name and structure.
# We will configure this in a 'vercel.json' file in the deployment guide.
async def handler(request):
    # 1. Basic validation and security checks
    if request.method != 'POST':
        return {
            "statusCode": 405,
            "body": json.dumps({"message": "Method Not Allowed"})
        }

    if not BOT_TOKEN or not GUILD_ID:
        print("ERROR: Bot token or Guild ID is not configured on the server.")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Server configuration error."})
        }

    try:
        body = json.loads(request.body)
        discord_username = body.get("discordUsername")
        cart = body.get("cart")
    except (json.JSONDecodeError, AttributeError):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid request body."})
        }

    if not discord_username or not cart:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing Discord username or cart items."})
        }
    
    # Split username (e.g., "user#1234") into name and discriminator
    try:
        name, discriminator = discord_username.split('#')
    except ValueError:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid Discord username format. Use user#1234."})
        }

    async with httpx.AsyncClient() as client:
        try:
            # 2. Find the Discord User ID
            # We search for the member in the specified guild
            search_url = f"{DISCORD_API_BASE_URL}/guilds/{GUILD_ID}/members/search?query={name}&limit=10"
            r = await client.get(search_url, headers=headers)
            r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            members = r.json()
            target_member = next((m for m in members if m['user']['discriminator'] == discriminator), None)

            if not target_member:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": f"User '{discord_username}' not found in the server."})
                }
            
            user_id = target_member['user']['id']

            # 3. Create a Direct Message (DM) channel with the user
            dm_channel_url = f"{DISCORD_API_BASE_URL}/users/@me/channels"
            dm_data = {"recipient_id": user_id}
            r = await client.post(dm_channel_url, headers=headers, json=dm_data)
            r.raise_for_status()
            dm_channel_id = r.json()['id']

            # 4. Construct and send the message
            messages = [item.get('message', f"Thank you for purchasing {item.get('name')}!") for item in cart]
            full_message = "Hello from the Affection Emporium!\n\n" + "\n".join(messages)
            
            message_url = f"{DISCORD_API_BASE_URL}/channels/{dm_channel_id}/messages"
            message_data = {"content": full_message}
            r = await client.post(message_url, headers=headers, json=message_data)
            r.raise_for_status()

            # 5. Send success response
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Successfully sent DM!"})
            }

        except httpx.HTTPStatusError as e:
            print(f"Discord API Error: {e.response.status_code} - {e.response.text}")
            error_body = {"message": "An error occurred while contacting Discord."}
            if e.response.status_code == 403:
                error_body["message"] = "Cannot send message. User may have DMs disabled or has blocked the bot."
            return {
                "statusCode": e.response.status_code,
                "body": json.dumps(error_body)
            }
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "An internal server error occurred."})
            }
