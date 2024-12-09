import os
import logging
import asyncio
import json
import requests
import random
from typing import Dict
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Firebase initialization function
def initialize_firebase():
    try:
        firebase_creds = os.getenv('FIREBASE_CREDENTIALS')

        if not firebase_creds:
            logger.error("No Firebase credentials found in environment variables.")
            return None

        try:
            if firebase_creds.startswith('http'):
                response = requests.get(firebase_creds)
                response.raise_for_status()
                cred_dict = response.json()
            else:
                cred_dict = json.loads(firebase_creds)
        except Exception as parsing_error:
            logger.error(f"Error parsing Firebase credentials: {parsing_error}")
            return None

        cred_path = '/tmp/firebase_credentials.json'
        with open(cred_path, 'w') as cred_file:
            json.dump(cred_dict, cred_file)

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()

        logger.info("Firebase initialized successfully.")
        return db

    except Exception as e:
        logger.error(f"Comprehensive Firebase initialization error: {e}")
        return None

# Initialize Firebase database
db = initialize_firebase()
if db is None:
    logger.error("Failed to initialize Firebase. Exiting.")
    exit(1)

# Ensure 'users' collection exists
def ensure_users_collection():
    try:
        users_ref = db.collection('users').document('default')
        if not users_ref.get().exists:
            users_ref.set({'created': True})
            logger.info("Default document added to 'users' collection.")
    except Exception as e:
        logger.error(f"Error ensuring users collection exists: {e}")

class InviteTrackerBot:
    def __init__(self, token: str):
        self.token = token
        self.invited_users = set()  # Track unique invited users

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.message.from_user
        user_ref = db.collection('users').document(str(user.id))
        user_data = user_ref.get()

        if not user_data.exists:
            user_ref.set({
                'invite_count': 0,
                'first_name': user.first_name,
                'withdrawal_key': None,
                'invited_user_ids': []  # Store IDs of invited users
            })

        user_data = user_ref.get().to_dict()
        invite_count = user_data['invite_count']
        first_name = user_data['first_name']
        balance = invite_count * 50
        remaining = max(200 - invite_count, 0)

        buttons = [
            [InlineKeyboardButton("Check", callback_data=f"check_{user.id}"),
             InlineKeyboardButton("Key🔑", callback_data=f"key_{user.id}")]
        ]

        if invite_count >= 200:
            message = (
                f"Congratulations 👏👏🎉\n\n"
                f"📊 Milestone Achieved: @DIGITAL_BIRRI\n"
                f"-----------------------\n"
                f"👤 User: {first_name}\n"
                f"👥 Invites: {invite_count} afeertaniittu! \n"
                f"💰 Balance: {balance} ETB\n"
                f"🚀 Baafachuuf: Baafachuu ni dandeessu! \n"
                f"-----------------------\n\n"
                f"Baafachuuf kan jedhu tuquun baafadhaa 👇"
            )
            buttons.append([
                InlineKeyboardButton(
                    "Withdrawal Request", 
                    url="https://t.me/your_withdrawal_bot_username"
                )
            ])
        else:
            message = (
                f"📊 Invite Progress: @DIGITAL_BIRRI\n"
                f"-----------------------\n"
                f"👤 User: {first_name}\n"
                f"👥 Invites: {invite_count} afeertaniittu \n"
                f"💰 Balance: {balance} ETB\n"
                f"🚀 Baafachuuf: Dabalataan nama {remaining} afeeraa\n"
                f"-----------------------\n\n"
                f"Add gochuun carraa badhaasaa keessan dabalaa!"
            )

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))

    async def handle_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user_id = query.data.split('_')[1]

        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get()

        if user_data.exists:
            user_data = user_data.to_dict()
            invite_count = user_data['invite_count']
            balance = invite_count * 50
            remaining = max(200 - invite_count, 0)
            first_name = user_data.get('first_name', 'User')

            # Pop-up alert with remaining invites
            await query.answer(
                f"Kabajamoo {first_name}, maallaqa baafachuuf dabalataan nama {remaining} afeeruu qabdu",
                show_alert=True
            )

            # Edit message to show current progress
            message = (
                f"📊 Invite Progress: @DIGITAL_BIRRI\n"
                f"-----------------------\n"
                f"👤 User: {first_name}\n"
                f"👥 Invites: {invite_count} afeertaniittu \n"
                f"💰 Balance: {balance} ETB\n"
                f"🚀 Baafachuuf: Dabalataan nama {remaining} afeeraa\n"
                f"-----------------------"
            )
            await query.edit_message_text(message)
        else:
            await query.answer("No user data found.", show_alert=True)

    async def handle_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user_id = query.data.split('_')[1]

        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()

        first_name = user_data.get('first_name', 'User')
        invite_count = user_data.get('invite_count', 0)
        withdrawal_key = user_data.get('withdrawal_key')

        if invite_count < 200:
            # Not enough invites
            await query.answer(
                f"Kabajamoo {first_name}, lakkoofsa Key argachuuf yoo xiqqaate nama 200 afeeruu qabdu!",
                show_alert=True
            )
        else:
            # Generate withdrawal key if not already exists
            if not withdrawal_key:
                withdrawal_key = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                user_ref.update({'withdrawal_key': withdrawal_key})

            # Show withdrawal key
            await query.answer(
                f"Kabajamoo {first_name}, Lakkoofsi Key🔑 keessanii: 👉{withdrawal_key}",
                show_alert=True
            )

    async def handle_withdrawal_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user_id = query.data.split('_')[1]

        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()

        if user_data.get('invite_count', 0) >= 200:
            # Redirect to withdrawal bot
            await query.answer("Redirecting to withdrawal request...")
            # Note: The actual redirection is handled by the URL in the button
        else:
            await query.answer("You have not yet reached the 200 invite milestone.", show_alert=True)

    async def track_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        for new_member in update.message.new_chat_members:
            try:
                inviter = update.message.from_user
                
                # Prevent self-invite
                if inviter.id == new_member.id:
                    continue

                # Prevent counting the same user multiple times
                if new_member.id in self.invited_users:
                    continue

                # Add to invited users set
                self.invited_users.add(new_member.id)

                # Update inviter's record
                user_ref = db.collection('users').document(str(inviter.id))
                user_data = user_ref.get()

                if not user_data.exists:
                    user_ref.set({
                        'invite_count': 0,
                        'first_name': inviter.first_name,
                        'withdrawal_key': None,
                        'invited_user_ids': []
                    })

                # Fetch current data
                user_data = user_ref.get().to_dict()
                
                # Get current invite count and invited user IDs
                invite_count = user_data.get('invite_count', 0)
                invited_user_ids = user_data.get('invited_user_ids', [])

                # Only increment if this user hasn't been invited before
                if new_member.id not in invited_user_ids:
                    # Update invite count
                    new_invite_count = invite_count + 1
                    
                    # Update invited users list
                    invited_user_ids.append(new_member.id)
                    
                    # Update Firestore
                    user_ref.update({
                        'invite_count': new_invite_count,
                        'invited_user_ids': invited_user_ids
                    })

                    logger.info(f"Tracked invite: {inviter.first_name} invited {new_member.first_name}")

            except Exception as e:
                logger.error(f"Error tracking invite: {e}")

    def run(self):
        try:
            application = Application.builder().token(self.token).build()

            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.track_new_member))
            application.add_handler(CallbackQueryHandler(self.handle_check, pattern=r'^check_\d+$'))
            application.add_handler(CallbackQueryHandler(self.handle_key, pattern=r'^key_\d+$'))
            application.add_handler(CallbackQueryHandler(self.handle_withdrawal_request, pattern=r'^withdraw_\d+$'))

            logger.info("Bot started successfully!")

            ensure_users_collection()

            asyncio.get_event_loop().run_until_complete(application.run_polling(drop_pending_updates=True))

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")

@app.route('/')
def index():
    return "Bot is running!"

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("No bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
        return

    bot = InviteTrackerBot(TOKEN)
    loop = asyncio.get_event_loop()
    loop.create_task(bot.run())

    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

if __name__ == "__main__":
    main()
