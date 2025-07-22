import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 1396766554028511372))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

def get_tg_nw_schedule():
    """
    Returns TG/NW based on scheduled times (5 minutes before):
    TG/NW: 1:55 AM, 4:55 AM, 7:55 AM, 10:55 AM, 1:55 PM, 4:55 PM, 7:55 PM, 10:55 PM
    """
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # TG/NW times: 5 minutes before 2, 5, 8, 11, 14, 17, 20, 23
    # So at: 1:55, 4:55, 7:55, 10:55, 13:55, 16:55, 19:55, 22:55
    reminder_hours = [1, 4, 7, 10, 13, 16, 19, 22]
    
    if current_hour in reminder_hours and current_minute == 55:
        # Calculate the actual event time (5 minutes later)
        event_hour = (current_hour + 1) % 24
        if event_hour in [2, 5, 8, 11, 14, 17, 20, 23]:
            event_time = f"{event_hour:02d}:00"
            # Convert to 12-hour format
            if event_hour == 0:
                formatted_time = "12:00 AM"
            elif event_hour < 12:
                formatted_time = f"{event_hour}:00 AM"
            elif event_hour == 12:
                formatted_time = "12:00 PM"
            else:
                formatted_time = f"{event_hour-12}:00 PM"
            return "TG/NW", formatted_time
    
    return None, now.strftime("%I:%M %p")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_health_server():
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Test if channel exists and bot can access it
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print(f'Found channel: {channel.name} in guild: {channel.guild.name}')
        try:
            await channel.send("🤖 Bot is now online!")

            print("Successfully sent test message")
        except discord.Forbidden:
            print("❌ No permission to send messages in this channel")
        except Exception as e:
            print(f"❌ Error sending message: {e}")
    else:
        print(f"❌ Channel with ID {CHANNEL_ID} not found")
    
    hourly_message.start()

#@tasks.loop(hours=1)
@tasks.loop(minutes=1)
async def hourly_message():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            event_type, event_time = get_tg_nw_schedule()
            if event_type:
                await channel.send(f"🚨 **{event_type}** event starting in 5 minutes at {event_time}! 🚨")
                print(f"Sent {event_type} reminder for {event_time}")
            # Remove the else block so it only sends messages during reminder times
        except discord.Forbidden:
            print("❌ No permission to send messages")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"❌ Channel {CHANNEL_ID} not found")

if TOKEN:
    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("Health check server started")
    
    bot.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not found in .env file")