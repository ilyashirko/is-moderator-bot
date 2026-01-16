import asyncio
import json
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from textwrap import dedent

import settings
from database import cruds
from settings import logger
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from utils import (
    ObsceneWordFound,
    check_obscene,
    extract_name,
    get_user_hash,
    startup_task,
)


async def block_user(
    chat_id: int,
    user_id: int,
    days: int,
    context: ContextTypes.DEFAULT_TYPE,
    reason: str,
):
    until = datetime.now(tz=timezone.utc) + timedelta(days=days)

    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        ),
        until_date=until,
    )
    await cruds.create_ban(telegram_user_id=user_id, reason=reason, period=days)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я жив 👋")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        dedent(
            """
                Доступные всем команды:
                
                /start
                /help

                Только для модераторов:

                /warn - "устное" предупреждение

                /strike - предупреждение с фиксацией удалением сообщений
                
                /ban {int} - блокировать на int дней
            """
        )
    )


async def strike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

    if update.message.from_user.id not in settings.MODERATORS_IDS or \
        update.message.reply_to_message.from_user.id in settings.MODERATORS_IDS:
        return
    
    if not update.message.reply_to_message:
        return
    
    update.message.reply_to_message.delete()

    await cruds.create_strike_record(
        telegram_user_id=update.message.reply_to_message.from_user.id,
        message=update.message.reply_to_message.text
        or update.message.reply_to_message.caption,
    )
    current_strikes = await cruds.count_strikes(
        telegram_user_id=update.message.reply_to_message.from_user.id
    )
    if current_strikes < settings.STRIKES_LIMIT:
        return await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=dedent(
                f"""
                    {await extract_name(update.message.reply_to_message.from_user)},
                    вы нарушили правила сообщества и заработали страйк.
                    
                    Еще {settings.STRIKES_LIMIT - current_strikes} и будет бан!
                
                """
            ),
            message_thread_id=settings.MODERATOR_TOPIC_ID,
        )

    user_bans_amount = await cruds.count_bans(
        telegram_user_id=update.message.reply_to_message.from_user.id
    )
    days = settings.BAN_LIMITS.get(user_bans_amount, 365)
    await block_user(
        chat_id=update.message.chat_id,
        user_id=update.message.reply_to_message.from_user.id,
        days=days,
        context=context,
        reason=update.message.reply_to_message.text
        or update.message.reply_to_message.caption,
    )
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent(
            f"""
            {await extract_name(update.message.reply_to_message.from_user)},
            вы нарушили правила сообщества и заработали страйк.
            
            Лимит страйков превышен, доступ в сообщество заблокирован на {days} дн."""
        ),
        message_thread_id=settings.MODERATOR_TOPIC_ID,
    )


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    if update.message.from_user.id not in settings.MODERATORS_IDS:
        return
    if not update.message.reply_to_message:
        return

    user_id = update.message.reply_to_message.from_user.id

    if user_id in settings.MODERATORS_IDS:
        return
    
    chat_id = update.effective_chat.id

    await update.message.reply_to_message.delete()

    try:
        days = int(context.args[0]) if context.args else 365
        if days < 1:
            days = 1
    except ValueError:
        days = 365

    await block_user(
        chat_id,
        user_id,
        days,
        context,
        reason=f"MANUAL BLOCK BY {update.message.from_user.id}\n\n{update.message.reply_to_message.text}",
    )
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"Пользователь {await extract_name(update.message.reply_to_message.from_user)} заблокирован на {days} дн.",
        message_thread_id=settings.MODERATOR_TOPIC_ID,
    )


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

    if update.message.from_user.id not in settings.MODERATORS_IDS:
        return
    if not update.message.reply_to_message:
        return
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent(
            f"""
                {await extract_name(update.message.reply_to_message.from_user)},
                на всякий случай напоминаю о действующих правилах сообщества!

                Ознакомиться с ними можно в соответствующем разделе "Правила группы"
            """
        ),
        message_thread_id=update.message.message_thread_id,
    )


async def delete_if_not_confirmed(
    chat_id: int | str,
    user_id: int,
    user_message_id: int | str,
    bot_message_id: int | str,
    context: ContextTypes.DEFAULT_TYPE,
    delay_seconds: int = 60,
):
    await asyncio.sleep(delay_seconds)

    user = await cruds.get_telegram_user(telegram_user_id=user_id)

    await context.bot.delete_message(chat_id=chat_id, message_id=bot_message_id)

    if user.confirmed:
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")


async def listen_all_mesages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with suppress(Exception):
        logger.info(json.dumps(update.message.to_dict(), ensure_ascii=False))

    user = await cruds.get_telegram_user(telegram_user_id=update.message.from_user.id)
    if not user:
        user = await cruds.create_telegram_user(**update.message.from_user.to_dict())

    if not user.confirmed:
        user_hash = await get_user_hash(user_data=update.message.from_user.to_dict())
        callback_data = f"user_confirmation_{update.message.from_user.id}"
        logger.info(f"{callback_data=}")
        message = await update.message.reply_text(
            dedent(
                f"""
                Привет, {await extract_name(update.message.from_user)}!

                Ты в сообществе "Дружелюбная сгущенка" где чтут порядок и уважение к друг другу (добровольно или принудительно).
                
                Ознакомься с правилами сообщества можно в разделе "Правила группы"

                но сперва подтверди что ты не бот, чтобы сообщения автоматически не удалялись (тык в кнопку ниже)
                """
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Я не бот и буду хорошим соседом",
                            callback_data=callback_data,
                        )
                    ]
                ]
            ),
        )
        asyncio.create_task(
            delete_if_not_confirmed(
                chat_id=update.message.chat_id,
                user_id=update.message.from_user.id,
                user_message_id=update.message.message_id,
                bot_message_id=message.id,
                context=context,
                delay_seconds=30,
            )
        )

    try:
        await check_obscene(text=update.message.text or update.message.caption)
    except ObsceneWordFound:
        if update.message.from_user.id in settings.MODERATORS_IDS:
            return
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"{await extract_name(update.message.from_user)}, у нас не матерятся!",
            message_thread_id=settings.MODERATOR_TOPIC_ID,
        )
        await update.message.delete()
        await cruds.create_strike_record(
            telegram_user_id=update.message.from_user.id,
            message=update.message.text or update.message.caption,
        )
        current_strikes = await cruds.count_strikes(
            telegram_user_id=update.message.from_user.id
        )
        if current_strikes < settings.STRIKES_LIMIT:
            return await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=dedent(
                    f"""
                        {await extract_name(update.message.from_user)},
                        вы нарушили правила сообщества и заработали страйк.
                        
                        Еще {settings.STRIKES_LIMIT - current_strikes} и будет бан!
                    
                    """
                ),
                message_thread_id=settings.MODERATOR_TOPIC_ID,
            )

        user_bans_amount = await cruds.count_bans(
            telegram_user_id=update.message.from_user.id
        )
        days = settings.BAN_LIMITS.get(user_bans_amount, 365)
        await block_user(
            chat_id=update.message.chat_id,
            user_id=update.message.from_user.id,
            days=days,
            context=context,
            reason=update.message.text
            or update.message.caption,
        )
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=dedent(
                f"""
                {await extract_name(update.message.from_user)},
                вы нарушили правила сообщества и заработали страйк.
                
                Лимит страйков превышен, доступ в сообщество заблокирован на {days} дн."""
            ),
            message_thread_id=settings.MODERATOR_TOPIC_ID,
        )

async def confirm_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_user_hash = await get_user_hash(update.callback_query.from_user.to_dict())
    button_user_hash = update.callback_query.data.rsplit("_", 1)[-1]

    current_user_id = update.callback_query.from_user.id
    try:
        button_user_id = int(update.callback_query.data.rsplit("_", 1)[-1])
        logger.info(f"{current_user_id=} {button_user_id=}")
        if button_user_id != current_user_id:
            return
        await cruds.confirm_telegram_user(
            telegram_user_id=update.callback_query.from_user.id
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            f"{await extract_name(update.callback_query.from_user)}, добро пожаловать!"
        )
    except ValueError as error:
        logger.exception(error)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Ошибка при обработке апдейта", exc_info=context.error)


def main():
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(startup_task)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("strike", strike))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("ban", ban))

    # Кнопки
    app.add_handler(CallbackQueryHandler(confirm_user, pattern="user_confirmation"))

    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.ALL, listen_all_mesages))

    # Обработчик ошибок
    app.add_error_handler(error_handler)

    # Long-polling
    app.run_polling(
        poll_interval=1.0,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
