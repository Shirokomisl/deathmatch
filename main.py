import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

NAMES_FILE = "predlozka.json"
PAGE_SIZE = 5

def load_names():
    try:
        with open(NAMES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

names_data = load_names()

def save_names():
    with open(NAMES_FILE, "w", encoding="utf-8") as file:
        json.dump(names_data, file, ensure_ascii=False, indent=4)

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args)
    if not name:
        await update.message.reply_text("Введите имя для предложения: /suggest <имя>")
        return

    if name not in names_data:
        names_data[name] = {"votes": 0, "priority": 0}
        save_names()
        await update.message.reply_text(f"Имя '{name}' добавлено в список предложений!")
    else:
        await update.message.reply_text("Это имя уже было предложено ранее.")

async def show_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = context.chat_data.get("page", 0)
    names = list(names_data.keys())
    if not names:
        await update.message.reply_text("Список предложенных имен пуст!")
        return

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    buttons = [
        [InlineKeyboardButton(f"{name} ❤️{data['votes']}", callback_data=f"like_{name}")]
        for name, data in list(names_data.items())[start:end]
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="page_prev"))
    if end < len(names):
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="page_next"))
    if nav_buttons:
        buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Список предложенных имен:", reply_markup=reply_markup)

async def paginate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "page_next":
        context.chat_data["page"] = context.chat_data.get("page", 0) + 1
    elif query.data == "page_prev":
        context.chat_data["page"] = max(context.chat_data.get("page", 0) - 1, 0)

    await query.answer()
    await show_names(update, context)

async def like_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    name = query.data.replace("like_", "")

    if name in names_data:
        names_data[name]["votes"] += 1
        save_names()
        await query.answer(f"Вы проголосовали за '{name}'.")
    else:
        await query.answer("Имя отсутствует в списке предложений.")

async def start_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(names_data) < 2:
        await update.message.reply_text("Недостаточно имен для проведения турнира.")
        return

    names = list(names_data.keys())
    random.shuffle(names)

    if len(names) % 2 != 0:
        await update.message.reply_text("Количество участников должно быть четным для турнира.")
        return

    context.chat_data["tournament_names"] = names
    context.chat_data["round"] = 1
    context.chat_data["match_index"] = 0
    await next_match(update, context)

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = context.chat_data["tournament_names"]
    match_index = context.chat_data["match_index"]

    if len(names) == 1:
        winner = names[0]
        save_names()
        await (update.message or update.callback_query.message).reply_text(f"Победитель турнира: {winner}!")
        return

    name1 = names.pop(0)
    name2 = names.pop(0)
    context.chat_data["current_match"] = [name1, name2]

    buttons = [
        [InlineKeyboardButton(f"{name1} ❤️{names_data[name1]['votes']}", callback_data=f"tournament_{name1}")],
        [InlineKeyboardButton(f"{name2} ❤️{names_data[name2]['votes']}", callback_data=f"tournament_{name2}")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await (update.message or update.callback_query.message).reply_text(
        f"Раунд {context.chat_data['round']}, Бой {match_index + 1}:", reply_markup=reply_markup
    )

async def handle_tournament_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    winner = query.data.replace("tournament_", "")

    if winner in names_data:
        names_data[winner]["votes"] += 1
        context.chat_data["tournament_names"].append(winner)
        context.chat_data["match_index"] += 1
        if context.chat_data["match_index"] >= len(context.chat_data["tournament_names"]) // 2:
            context.chat_data["round"] += 1
            context.chat_data["match_index"] = 0

        await next_match(update, context)
        await query.answer(f"Вы проголосовали за '{winner}'.")
    else:
        await query.answer("Ошибка! Имя отсутствует в списке предложений.")

def main():
    app = Application.builder().token("8007253142:AAGHhUWaD4yZq12t0Bwk0H8LzY90qvmuHhY").build()

    app.add_handler(CommandHandler("suggest", suggest))
    app.add_handler(CommandHandler("show_names", show_names))
    app.add_handler(CommandHandler("tournament", start_tournament))
    app.add_handler(CallbackQueryHandler(paginate, pattern="^page_"))
    app.add_handler(CallbackQueryHandler(like_name, pattern="^like_"))
    app.add_handler(CallbackQueryHandler(handle_tournament_vote, pattern="^tournament_"))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

