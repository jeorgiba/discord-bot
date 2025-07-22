import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 1396766554028511372))
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Lisbon')  # Follow Lisbon time for notifications

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for commands
bot = commands.Bot(command_prefix='!', intents=intents)

def get_nation_war_schedule():
    """
    Returns Nation War based on scheduled times (5 minutes before) in Lisbon time:
    Nation War: 1:55 AM, 4:55 AM, 7:55 AM, 10:55 AM, 1:55 PM, 4:55 PM, 7:55 PM, 10:55 PM (Lisbon time)
    """
    # Get current time in Lisbon timezone
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute

    # Nation War times: 5 minutes before 2, 5, 8, 11, 14, 17, 20, 23 (Lisbon time)
    # So at: 1:55, 4:55, 7:55, 10:55, 13:55, 16:55, 19:55, 22:55 (Lisbon time)
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
            return "Nation War", formatted_time

    return None, now.strftime("%I:%M %p")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-Length', '15')
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-Length', '15')
        self.end_headers()
    
    def do_POST(self):
        self.do_GET()
    
    def do_PUT(self):
        self.do_GET()
    
    def do_DELETE(self):
        self.do_GET()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Allow', 'GET, HEAD, POST, PUT, DELETE, OPTIONS')
        self.send_header('Content-Length', '0')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging to reduce noise
        pass

def run_health_server():
    port = int(os.getenv('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"Health server starting on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Health server error: {e}")
        # Continue without health server if it fails

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

@bot.command(name='test')
async def test_notification(ctx):
    """Test command to send a sample notification"""
    await ctx.send("🚨 **Nation War** event starting in 5 minutes at 2:00 AM! 🚨")
    print("Test notification sent!")

@bot.command(name='schedule')
async def check_schedule(ctx):
    """Check the current schedule status"""
    event_type, event_time = get_nation_war_schedule()
    tz = pytz.timezone(TIMEZONE)
    current_time = datetime.now(tz).strftime("%I:%M %p")
    
    # Also show Manila time
    manila_tz = pytz.timezone('Asia/Manila')
    manila_time = datetime.now(manila_tz).strftime("%I:%M %p")
    
    if event_type:
        await ctx.send(f"📅 Next event: **{event_type}** at {event_time} (Lisbon time)")
    else:
        await ctx.send(f"📅 No events scheduled right now.\n"
                      f"Current time (Lisbon): {current_time}\n"
                      f"Current time (Manila): {manila_time}")
    
    # Show next reminder times
    reminder_times = ["1:55 AM", "4:55 AM", "7:55 AM", "10:55 AM", "1:55 PM", "4:55 PM", "7:55 PM", "10:55 PM"]
    await ctx.send(f"🕐 Reminder times (Lisbon time): {', '.join(reminder_times)}")

@bot.command(name='times')
async def show_all_times(ctx):
    """Show all Nation War event times in Lisbon and Manila time"""
    lisbon_tz = pytz.timezone('Europe/Lisbon')
    manila_tz = pytz.timezone('Asia/Manila')
    
    # Event times in Lisbon (24-hour format)
    event_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    
    schedule_text = "🌍 **Nation War Schedule:**\n\n"
    
    for hour in event_hours:
        # Create Lisbon time
        lisbon_time = datetime.now(lisbon_tz).replace(hour=hour, minute=0, second=0, microsecond=0)
        
        # Convert to Manila time
        manila_time = lisbon_time.astimezone(manila_tz)
        
        # Format times
        lisbon_12h = lisbon_time.strftime("%I:%M %p").lstrip('0')
        manila_12h = manila_time.strftime("%I:%M %p").lstrip('0')
        
        schedule_text += f"Lisbon: **{lisbon_12h}** → Manila: **{manila_12h}**\n"
    
    await ctx.send(schedule_text)

@bot.command(name='debug')
async def debug_time(ctx):
    """Debug current time and schedule logic"""
    # Get Lisbon, UTC, and Manila time for comparison
    lisbon_tz = pytz.timezone('Europe/Lisbon')
    lisbon_now = datetime.now(lisbon_tz)
    utc_now = datetime.now(pytz.UTC)
    manila_tz = pytz.timezone('Asia/Manila')
    manila_now = datetime.now(manila_tz)
    
    current_hour = lisbon_now.hour
    current_minute = lisbon_now.minute
    
    await ctx.send(f"🐛 **Debug Info:**\n"
                  f"Current time (Lisbon): {lisbon_now.strftime('%H:%M')} (24h) / {lisbon_now.strftime('%I:%M %p')} (12h)\n"
                  f"Current time (Manila): {manila_now.strftime('%H:%M')} (24h) / {manila_now.strftime('%I:%M %p')} (12h)\n"
                  f"UTC time: {utc_now.strftime('%H:%M')} (24h) / {utc_now.strftime('%I:%M %p')} (12h)\n"
                  f"Hour: {current_hour}, Minute: {current_minute}\n"
                  f"Is reminder hour: {current_hour in [1, 4, 7, 10, 13, 16, 19, 22]}\n"
                  f"Is minute 55: {current_minute == 55}\n"
                  f"Is minute 59: {current_minute == 59}")
    
    # Test what would happen at next reminder time
    if current_hour in [1, 4, 7, 10, 13, 16, 19, 22]:
        event_hour = (current_hour + 1) % 24
        if event_hour in [2, 5, 8, 11, 14, 17, 20, 23]:
            if event_hour == 0:
                formatted_time = "12:00 AM"
            elif event_hour < 12:
                formatted_time = f"{event_hour}:00 AM"
            elif event_hour == 12:
                formatted_time = "12:00 PM"
            else:
                formatted_time = f"{event_hour-12}:00 PM"
            
            # Calculate Manila time for the event
            lisbon_event = lisbon_now.replace(hour=event_hour, minute=0, second=0, microsecond=0)
            manila_event = lisbon_event.astimezone(manila_tz)
            manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
            
            await ctx.send(f"Next Nation War event:\n"
                          f"Lisbon: {formatted_time}\n"
                          f"Manila: {manila_formatted}")

@tasks.loop(minutes=1)
async def hourly_message():
    # Check at :55 (5-min warning) and :59 (1-min warning) of each hour in Lisbon time
    tz = pytz.timezone(TIMEZONE)  # Europe/Lisbon
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute
    
    # Only proceed if it's :55 or :59 minutes
    if current_minute not in [55, 59]:
        return
    
    # Check if this is a Nation War hour in Lisbon time
    # Events at: 2, 5, 8, 11, 14, 17, 20, 23 (Lisbon time)
    # So reminders at: 1, 4, 7, 10, 13, 16, 19, 22 (Lisbon time)
    reminder_hours = [1, 4, 7, 10, 13, 16, 19, 22]
    if current_hour not in reminder_hours:
        return
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            # Calculate the event time
            event_hour = (current_hour + 1) % 24
            # Double-check this is a valid event hour
            if event_hour in [2, 5, 8, 11, 14, 17, 20, 23]:
                # Convert to 12-hour format
                if event_hour == 0:
                    formatted_time = "12:00 AM"
                elif event_hour < 12:
                    formatted_time = f"{event_hour}:00 AM"
                elif event_hour == 12:
                    formatted_time = "12:00 PM"
                else:
                    formatted_time = f"{event_hour-12}:00 PM"
                
                # Calculate Manila time for the event
                manila_tz = pytz.timezone('Asia/Manila')
                lisbon_event = now.replace(hour=event_hour, minute=0, second=0, microsecond=0)
                manila_event = lisbon_event.astimezone(manila_tz)
                manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
                
                # Different messages for 5-min and 1-min warnings
                if current_minute == 55:
                    message = f"🚨 **Nation War** event starting in 5 minutes at {formatted_time} (Lisbon time) / {manila_formatted} (Manila time)! 🚨"
                    log_msg = f"✅ Sent 5-minute Nation War reminder for {formatted_time} Lisbon / {manila_formatted} Manila"
                else:  # current_minute == 59
                    message = f"⚠️ **Nation War** event starting in 1 minute at {formatted_time} (Lisbon time) / {manila_formatted} (Manila time)! Get ready! ⚠️"
                    log_msg = f"✅ Sent 1-minute Nation War reminder for {formatted_time} Lisbon / {manila_formatted} Manila"
                
                await channel.send(message)
                current_time = now.strftime("%H:%M")
                
                # Also show UTC time in log for reference
                utc_now = datetime.now(pytz.UTC)
                print(f"[{current_time} Lisbon / {utc_now.strftime('%H:%M')} UTC] {log_msg}")
            else:
                current_time = now.strftime("%H:%M")
                print(f"⏰ No event scheduled at {current_time} Lisbon time")
        except discord.Forbidden:
            print("❌ No permission to send messages")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"❌ Channel {CHANNEL_ID} not found")

if TOKEN:
    # Start health check server in background thread
    try:
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        print("Health check server started")
    except Exception as e:
        print(f"Failed to start health server: {e}")
    
    # Start the Discord bot
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Bot error: {e}")
else:
    print("Error: DISCORD_BOT_TOKEN not found in .env file")