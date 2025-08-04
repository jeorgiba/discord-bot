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

def get_world_boss_schedule():
    """
    Returns World Boss based on scheduled times in Lisbon time (1 minute before events):
    World Boss warnings: 12:59 AM, 1:09 AM, 5:59 AM, 6:09 AM, 10:59 AM, 11:09 AM, 
                        3:59 PM, 4:09 PM, 4:19 PM, 8:59 PM, 9:09 PM
    """
    # Get current time in Lisbon timezone
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute

    # World Boss warning times (1 minute before actual events)
    world_boss_warnings = {
        0: [59],         # 12:59 AM for 1:00 AM event
        1: [9],          # 1:09 AM for 1:10 AM event
        5: [59],         # 5:59 AM for 6:00 AM event
        6: [9],          # 6:09 AM for 6:10 AM event
        10: [59],        # 10:59 AM for 11:00 AM event
        11: [9],         # 11:09 AM for 11:10 AM event
        15: [59],        # 3:59 PM for 4:00 PM event
        16: [9, 19],     # 4:09 PM for 4:10 PM, 4:19 PM for 4:20 PM event
        20: [59],        # 8:59 PM for 9:00 PM event
        21: [9]          # 9:09 PM for 9:10 PM event
    }
    
    if current_hour in world_boss_warnings and current_minute in world_boss_warnings[current_hour]:
        # Calculate the actual event time (1 minute later)
        event_hour = current_hour
        event_minute = (current_minute + 1) % 60
        if current_minute == 59:
            event_hour = (current_hour + 1) % 24
            event_minute = 0
        
        # Convert to 12-hour format
        if event_hour == 0:
            formatted_time = f"12:{event_minute:02d} AM"
        elif event_hour < 12:
            formatted_time = f"{event_hour}:{event_minute:02d} AM"
        elif event_hour == 12:
            formatted_time = f"12:{event_minute:02d} PM"
        else:
            formatted_time = f"{event_hour-12}:{event_minute:02d} PM"
        
        return "World Boss", formatted_time, current_minute

    return None, now.strftime("%I:%M %p"), None

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
    await ctx.send("⚔️ Nation War in 5min at 2:00 AM! ⚔️")
    print("Test notification sent!")

@bot.command(name='testwb')
async def test_world_boss(ctx):
    """Test command to send a sample World Boss notification"""
    await ctx.send("� World Boss NOW at 4:00 PM Lisbon / 11:00 PM Manila! �")
    print("Test World Boss notification sent!")

@bot.command(name='schedule')
async def check_schedule(ctx):
    """Check the current schedule status"""
    tz = pytz.timezone(TIMEZONE)
    manila_tz = pytz.timezone('Asia/Manila')
    current_time = datetime.now(tz).strftime("%I:%M %p")
    manila_time = datetime.now(manila_tz).strftime("%I:%M %p")
    
    # Check Nation War
    nation_war_event, nation_war_time = get_nation_war_schedule()
    
    # Check World Boss
    world_boss_event, world_boss_time, _ = get_world_boss_schedule()
    
    if nation_war_event or world_boss_event:
        schedule_text = "📅 Upcoming Events:\n"
        if nation_war_event:
            schedule_text += f"⚔️ {nation_war_event} at {nation_war_time} (Lisbon time)\n"
        if world_boss_event:
            schedule_text += f"� {world_boss_event} at {world_boss_time} (Lisbon time)\n"
        await ctx.send(schedule_text)
    else:
        await ctx.send(f"📅 No events scheduled right now.\n"
                      f"Current time (Lisbon): {current_time}\n"
                      f"Current time (Manila): {manila_time}")
    
    # Show Nation War reminder times
    reminder_times = ["1:55 AM", "4:55 AM", "7:55 AM", "10:55 AM", "1:55 PM", "4:55 PM", "7:55 PM", "10:55 PM"]
    await ctx.send(f"⚔️ Nation War reminders (Lisbon time): {', '.join(reminder_times)}")
    
    # Show World Boss warning times
    world_boss_times = ["12:59 AM → 1:00 AM", "1:09 AM → 1:10 AM", "5:59 AM → 6:00 AM", "6:09 AM → 6:10 AM", "10:59 AM → 11:00 AM", "11:09 AM → 11:10 AM", "3:59 PM → 4:00 PM", "4:09 PM → 4:10 PM", "4:19 PM → 4:20 PM", "8:59 PM → 9:00 PM", "9:09 PM → 9:10 PM"]
    await ctx.send(f"� World Boss 1-min warnings (Lisbon time): {', '.join(world_boss_times)}")

@bot.command(name='times')
async def show_all_times(ctx):
    """Show all event times in Lisbon and Manila time"""
    lisbon_tz = pytz.timezone('Europe/Lisbon')
    manila_tz = pytz.timezone('Asia/Manila')
    
    schedule_text = "🌍 Complete Event Schedule:\n\n"
    
    # Nation War Schedule
    schedule_text += "⚔️ Nation War Events:\n"
    nation_war_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    
    for hour in nation_war_hours:
        lisbon_time = datetime.now(lisbon_tz).replace(hour=hour, minute=0, second=0, microsecond=0)
        manila_time = lisbon_time.astimezone(manila_tz)
        
        lisbon_12h = lisbon_time.strftime("%I:%M %p").lstrip('0')
        manila_12h = manila_time.strftime("%I:%M %p").lstrip('0')
        
        schedule_text += f"Lisbon: {lisbon_12h} → Manila: {manila_12h}\n"
    
    # World Boss Schedule
    schedule_text += "\n� World Boss Events:\n"
    world_boss_times = [
        (1, [0, 10]),      # 1:00 AM & 1:10 AM
        (6, [0, 10]),      # 6:00 AM & 6:10 AM  
        (11, [0, 10]),     # 11:00 AM & 11:10 AM
        (16, [0, 10, 20]), # 4:00 PM & 4:10 PM & 4:20 PM
        (21, [0, 10])      # 9:00 PM & 9:10 PM
    ]
    
    for hour, minutes in world_boss_times:
        for minute in minutes:
            lisbon_time = datetime.now(lisbon_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
            manila_time = lisbon_time.astimezone(manila_tz)
            
            lisbon_12h = lisbon_time.strftime("%I:%M %p").lstrip('0')
            manila_12h = manila_time.strftime("%I:%M %p").lstrip('0')
            
            schedule_text += f"Lisbon: {lisbon_12h} → Manila: {manila_12h}\n"
    
    await ctx.send(schedule_text)

@bot.command(name='worldboss')
async def show_world_boss_times(ctx):
    """Show World Boss event times in Lisbon and Manila time"""
    lisbon_tz = pytz.timezone('Europe/Lisbon')
    manila_tz = pytz.timezone('Asia/Manila')
    
    schedule_text = "� World Boss Schedule:\n\n"
    
    world_boss_times = [
        (1, [0, 10]),      # 1:00 AM & 1:10 AM
        (6, [0, 10]),      # 6:00 AM & 6:10 AM  
        (11, [0, 10]),     # 11:00 AM & 11:10 AM
        (16, [0, 10, 20]), # 4:00 PM & 4:10 PM & 4:20 PM
        (21, [0, 10])      # 9:00 PM & 9:10 PM
    ]
    
    for hour, minutes in world_boss_times:
        time_list = []
        manila_time_list = []
        
        for minute in minutes:
            lisbon_time = datetime.now(lisbon_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
            manila_time = lisbon_time.astimezone(manila_tz)
            
            lisbon_12h = lisbon_time.strftime("%I:%M %p").lstrip('0')
            manila_12h = manila_time.strftime("%I:%M %p").lstrip('0')
            
            time_list.append(lisbon_12h)
            manila_time_list.append(manila_12h)
        
        schedule_text += f"Lisbon: {' & '.join(time_list)} → Manila: {' & '.join(manila_time_list)}\n"
    
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
    
    await ctx.send(f"🐛 Debug Info:\n"
                  f"Current time (Lisbon): {lisbon_now.strftime('%H:%M')} (24h) / {lisbon_now.strftime('%I:%M %p')} (12h)\n"
                  f"Current time (Manila): {manila_now.strftime('%H:%M')} (24h) / {manila_now.strftime('%I:%M %p')} (12h)\n"
                  f"UTC time: {utc_now.strftime('%H:%M')} (24h) / {utc_now.strftime('%I:%M %p')} (12h)\n"
                  f"Hour: {current_hour}, Minute: {current_minute}\n"
                  f"Nation War reminder hour: {current_hour in [1, 4, 7, 10, 13, 16, 19, 22]}\n"
                  f"Is minute 55/59: {current_minute in [55, 59]}\n"
                  f"World Boss warning hour: {current_hour in [0, 1, 5, 6, 10, 11, 15, 16, 20, 21]}\n"
                  f"Is minute 59/09/19: {current_minute in [59, 9, 19]}")
    
    # Check for upcoming events
    events_info = ""
    
    # Test Nation War
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
            
            lisbon_event = lisbon_now.replace(hour=event_hour, minute=0, second=0, microsecond=0)
            manila_event = lisbon_event.astimezone(manila_tz)
            manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
            
            events_info += f"⚔️ Next Nation War:\nLisbon: {formatted_time}\nManila: {manila_formatted}\n\n"
    
    # Test World Boss
    world_boss_warnings = {
        0: [59],         # 12:59 AM for 1:00 AM event
        1: [9],          # 1:09 AM for 1:10 AM event
        5: [59],         # 5:59 AM for 6:00 AM event
        6: [9],          # 6:09 AM for 6:10 AM event
        10: [59],        # 10:59 AM for 11:00 AM event
        11: [9],         # 11:09 AM for 11:10 AM event
        15: [59],        # 3:59 PM for 4:00 PM event
        16: [9, 19],     # 4:09 PM for 4:10 PM, 4:19 PM for 4:20 PM event
        20: [59],        # 8:59 PM for 9:00 PM event
        21: [9]          # 9:09 PM for 9:10 PM event
    }
    
    if current_hour in world_boss_warnings:
        upcoming_minutes = [m for m in world_boss_warnings[current_hour] if m >= current_minute]
        if upcoming_minutes:
            next_minute = upcoming_minutes[0]
            # Calculate the actual event time (1 minute after warning)
            event_hour = current_hour
            event_minute = (next_minute + 1) % 60
            if next_minute == 59:
                event_hour = (current_hour + 1) % 24
                event_minute = 0
            
            if event_hour == 0:
                formatted_time = f"12:{event_minute:02d} AM"
            elif event_hour < 12:
                formatted_time = f"{event_hour}:{event_minute:02d} AM"
            elif event_hour == 12:
                formatted_time = f"12:{event_minute:02d} PM"
            else:
                formatted_time = f"{event_hour-12}:{event_minute:02d} PM"
            
            lisbon_event = lisbon_now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
            manila_event = lisbon_event.astimezone(manila_tz)
            manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
            
            events_info += f"� Next World Boss:\nLisbon: {formatted_time}\nManila: {manila_formatted}"
    
    if events_info:
        await ctx.send(events_info)
    else:
        await ctx.send("No immediate events scheduled.")

@tasks.loop(minutes=1)
async def hourly_message():
    # Check for both Nation War and World Boss events
    tz = pytz.timezone(TIMEZONE)  # Europe/Lisbon
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Channel {CHANNEL_ID} not found")
        return
    
    manila_tz = pytz.timezone('Asia/Manila')
    
    try:
        # Check for Nation War (at :55 and :59 minutes)
        if current_minute in [55, 59]:
            reminder_hours = [1, 4, 7, 10, 13, 16, 19, 22]
            if current_hour in reminder_hours:
                event_hour = (current_hour + 1) % 24
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
                    lisbon_event = now.replace(hour=event_hour, minute=0, second=0, microsecond=0)
                    manila_event = lisbon_event.astimezone(manila_tz)
                    manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
                    
                    # Different messages for 5-min and 1-min warnings
                    if current_minute == 55:
                        message = f"⚔️ Nation War in 5min at {formatted_time} Lisbon / {manila_formatted} Manila! ⚔️"
                        log_msg = f"✅ Sent 5-minute Nation War reminder for {formatted_time} Lisbon / {manila_formatted} Manila"
                    else:  # current_minute == 59
                        message = f"⚔️ Nation War in 1min at {formatted_time} Lisbon / {manila_formatted} Manila! Ready! ⚔️"
                        log_msg = f"✅ Sent 1-minute Nation War reminder for {formatted_time} Lisbon / {manila_formatted} Manila"
                    
                    await channel.send(message)
                    current_time = now.strftime("%H:%M")
                    utc_now = datetime.now(pytz.UTC)
                    print(f"[{current_time} Lisbon / {utc_now.strftime('%H:%M')} UTC] {log_msg}")
        
        # Check for World Boss events (1 minute before: at :59, :09, :19 minutes)
        if current_minute in [59, 9, 19]:
            world_boss_schedule = {
                0: [59],         # 12:59 AM for 1:00 AM event
                1: [9],          # 1:09 AM for 1:10 AM event
                5: [59],         # 5:59 AM for 6:00 AM event
                6: [9],          # 6:09 AM for 6:10 AM event
                10: [59],        # 10:59 AM for 11:00 AM event
                11: [9],         # 11:09 AM for 11:10 AM event
                15: [59],        # 3:59 PM for 4:00 PM event
                16: [9, 19],     # 4:09 PM for 4:10 PM, 4:19 PM for 4:20 PM event
                20: [59],        # 8:59 PM for 9:00 PM event
                21: [9]          # 9:09 PM for 9:10 PM event
            }
            
            if current_hour in world_boss_schedule and current_minute in world_boss_schedule[current_hour]:
                # Calculate the actual event time (1 minute later)
                event_hour = current_hour
                event_minute = (current_minute + 1) % 60
                if current_minute == 59:
                    event_hour = (current_hour + 1) % 24
                    event_minute = 0
                
                # Convert to 12-hour format
                if event_hour == 0:
                    formatted_time = f"12:{event_minute:02d} AM"
                elif event_hour < 12:
                    formatted_time = f"{event_hour}:{event_minute:02d} AM"
                elif event_hour == 12:
                    formatted_time = f"12:{event_minute:02d} PM"
                else:
                    formatted_time = f"{event_hour-12}:{event_minute:02d} PM"
                
                # Calculate Manila time for the event
                lisbon_event = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
                manila_event = lisbon_event.astimezone(manila_tz)
                manila_formatted = manila_event.strftime("%I:%M %p").lstrip('0')
                
                message = f"� World Boss in 1min at {formatted_time} Lisbon / {manila_formatted} Manila! Ready! �"
                log_msg = f"✅ Sent 1-minute World Boss reminder for {formatted_time} Lisbon / {manila_formatted} Manila"
                
                await channel.send(message)
                current_time = now.strftime("%H:%M")
                utc_now = datetime.now(pytz.UTC)
                print(f"[{current_time} Lisbon / {utc_now.strftime('%H:%M')} UTC] {log_msg}")
                
    except discord.Forbidden:
        print("❌ No permission to send messages")
    except Exception as e:
        print(f"❌ Error: {e}")

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