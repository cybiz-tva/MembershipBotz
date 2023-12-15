import logging
import telegram
import json
import subprocess
import time
from datetime import datetime, timedelta
from telegram.ext import CommandHandler, Updater

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Set up bot and channel IDs
TOKEN = 'YOUR_TOKEN_HERE'
channel_id = '@your_channel_username'  # Replace with your channel username or ID
OWNER_ID = OWNER_ID_HERE

# Path to files
DATA_FILE = 'schedule.json'
CODES_FILE = 'codes.txt'

bot = telegram.Bot(TOKEN)

# On /start replies with welcome msg
def start(update, context):
    user_id = update.effective_user.id
    chat_info = bot.get_chat(chat_id=user_id)
    username = chat_info.username

    bot.send_message(chat_id=user_id,
                     text=f"WELCOME!\nThat's the /start reply message.",
                     parse_mode="HTML")

# Reads data from JSON
def read_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    return data

# Writes data on JSON
def write_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Process the ban/kick process.
def remove_user(context):
    user_id = context['user_id']
    try:
        bot.kick_chat_member(chat_id=channel_id, user_id=user_id)
        logging.info(f"User {user_id} removed from channel {channel_id}")
        bot.send_message(chat_id=OWNER_ID,
                         text=f"❌ <b>REMOVED</b>: <a href='tg://user?id={user_id}'>{user_id}</a> from channel.",
                         parse_mode="HTML")
        bot.send_message(chat_id=user_id,
                         text=f"❌ <b>LICENSE EXPIRED</b>",
                         parse_mode="HTML")
    except telegram.error.BadRequest:
        logging.error(f"Failed to remove user {user_id} from channel {channel_id}")
    data = read_data()
    if str(user_id) in data:
        del data[str(user_id)]
        write_data(data)

# Handles /redeem command
def redeem(update, context):
    try:
        # Get user ID and code from command
        user_id = str(update.effective_user.id)
        code = context.args[0]

        # Check if code exists in file
        with open(CODES_FILE) as f:
            codes = f.read().splitlines()
        if code in codes:
            d = int(code[0])  # Extract duration from the first digit of the code

            try:
                bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
            except:
                pass

            data = read_data()

            if str(user_id) in data:
                job_data = data[user_id]
                old_date = datetime.fromisoformat(job_data['removal_date'])
                removal_date = old_date + timedelta(days=d)
                logging.info(f"{user_id} already exists, adding {d} days to {old_date}")
            else:
                removal_date = datetime.now() + timedelta(days=d)
                logging.info(f"{user_id} doesn't exist, adding {d} days to {datetime.now}")

            data[str(user_id)] = {'removal_date': removal_date.isoformat()}
            write_data(data)
            logging.info("Scheduled task saved to JSON file")

            chat_info = bot.get_chat(chat_id=user_id)
            username = chat_info.username

            bot.send_message(chat_id=user_id,
                             text=f"<b>✅ License redeemed!</b>\n\nHi <a href='tg://user?id={user_id}'>{username}</a>\nAdded {d} days access.\n\n<b>Expire</b>: {removal_date}",
                             parse_mode="HTML")

            bot.send_message(chat_id=OWNER_ID,
                             text=f"<b>Username</b>: {username}\n<b>ID</b>: <a href='tg://user?id={user_id}'>{user_id}</a> \n<b>Code</b>: {code} - {d} days\n<b>Expire</b>: {removal_date}",
                             parse_mode="HTML")

            def read_codes():
                with open(CODES_FILE, 'r') as f:
                    return f.read().splitlines()

            def write_codes(codes):
                with open(CODES_FILE, 'w') as f:
                    f.write('\n'.join(codes))

            codesf = read_codes()
            codesf.remove(code)
            write_codes(codesf)
        else:
            update.message.reply_text("Invalid code.\nUsage: /redeem <license_here>")
    except:
        logging.error(f"Error in redeem")
        update.message.reply_text("Invalid code.\nUsage: /redeem <license_here>")

# On start verifies expired memberships
def load_jobs():
    data = read_data()
    for user_id, job_data in data.items():
        removal_date = datetime.fromisoformat(job_data['removal_date'])
        if removal_date < datetime.now():
            job_data = {'user_id': int(user_id)}
            remove_user(context=job_data)

# Main function
def main():
    # Set up dispatcher and job queue
    updater = telegram.ext.Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register command handlers
    dp.add_handler(telegram.ext.CommandHandler('start', start))
    dp.add_handler(telegram.ext.CommandHandler('help', start))
    dp.add_handler(telegram.ext.CommandHandler('redeem', redeem))

    # Load scheduled removal jobs
    load_jobs()

    # Start the bot
    updater.start_polling()
    logging.info("Bot started")
    updater.idle()

# Code for restarting the bot every X amount of time
while True:
    bot_process = subprocess.Popen(['python', __file__])

    # Wait for given amount of seconds
    time.sleep(43200)  # That's 12 hours

    # Terminate the bot.py process
    bot_process.terminate()

if __name__ == '__main__':
    main()
