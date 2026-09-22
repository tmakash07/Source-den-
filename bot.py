import os
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from tavily import TavilyClient


BOT_TOKEN = os.getenv("BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not BOT_TOKEN or not TAVILY_API_KEY:
    raise RuntimeError("BOT_TOKEN or TAVILY_API_KEY is missing.")

tavily = TavilyClient(api_key=TAVILY_API_KEY)


def search_sources(query):
    searches = [
        f'"{query}"',
        query,
        f"{query} news",
    ]

    results = []

    for search_query in searches:
        try:
            response = tavily.search(
                query=search_query,
                search_depth="advanced",
                max_results=8,
                include_answer=False,
            )

            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "published": item.get("published_date"),
                })

        except Exception as e:
            print("Search error:", e)

    # Remove duplicate URLs
    unique = {}
    for item in results:
        url = item["url"]
        if url and url not in unique:
            unique[url] = item

    return list(unique.values())


def format_result(query, results):
    text = "🔎 <b>SOURCE INVESTIGATION</b>\n\n"
    text += f"<b>Claim:</b>\n{query}\n\n"
    text += "━━━━━━━━━━━━━━\n\n"

    if not results:
        return text + "❌ কোনো relevant source পাওয়া যায়নি।"

    # Put dated results first
    dated = [r for r in results if r.get("published")]
    undated = [r for r in results if not r.get("published")]

    dated.sort(key=lambda x: x["published"])

    ordered = dated + undated

    for i, item in enumerate(ordered[:10], 1):
        title = item["title"]
        url = item["url"]
        published = item.get("published")

        if published:
            try:
                dt = datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                )
                date_text = dt.strftime("%d %b %Y")
            except Exception:
                date_text = published
        else:
            date_text = "Date unavailable"

        text += f"<b>{i}. {title}</b>\n"
        text += f"📅 {date_text}\n"
        text += f"🔗 <a href=\"{url}\">Open Source</a>\n\n"

    text += "━━━━━━━━━━━━━━\n"
    text += (
        "⚠️ <b>Note:</b> Earliest result means the earliest "
        "dated source found by the search engine. "
        "It does not necessarily prove the original creator."
    )

    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 <b>Source Finder</b>\n\n"
        "যে খবর/তথ্যের earliest online source খুঁজতে চাও, "
        "সেটা শুধু এখানে পাঠাও।",
        parse_mode="HTML",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    msg = await update.message.reply_text(
        "🔍 Searching sources...\n\n"
        "একটু সময় লাগতে পারে।"
    )

    try:
        results = await asyncio.to_thread(search_sources, query)

        response = format_result(query, results)

        await msg.edit_text(
            response,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    except Exception as e:
        print("Bot error:", e)

        await msg.edit_text(
            "❌ Search করতে সমস্যা হয়েছে।\n\n"
            "কিছুক্ষণ পর আবার চেষ্টা করো।"
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Source Finder Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
