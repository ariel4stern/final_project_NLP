"""Gradio web UI for the SQLite + LangChain restaurant chatbot."""

from dotenv import load_dotenv
import gradio as gr
from restaurant_telegram_chatbot import RestaurantTelegramChatbot
from dal_rst_telegram import initialize_database,DB_PATH


def create_bot(db_path: str = DB_PATH) -> RestaurantTelegramChatbot:

    load_dotenv()
    initialize_database(db_path)

    return RestaurantTelegramChatbot(db_path=db_path)

def build_demo(bot: RestaurantTelegramChatbot) -> gr.Blocks:

    def manager_confirmation(history):
        history = history or []

        result = bot.confirm_events()

        history.append({
            "role": "assistant",
            "content": f"Manager confirmed {result} reservations"
        })

        return history

    def chat_handler(message: str, history: list[dict]) -> tuple[list[dict[str,str]], str]:
        history = history or []
        user_text = (message or "").strip()
        if not user_text:
            return history, ""

        sliced_history = history[-10:]

        answer = bot.answer(user_text,sliced_history)
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": answer})

        return history, ""

    with gr.Blocks(title="Restaurant Chatbot") as demo:
        gr.Markdown("## Restaurant Chatbot\nAsk about menu items, prices, or opening hours.")

        chatbot = gr.Chatbot(label="Conversation", height=260)
        message_box = gr.Textbox(label="Your question", placeholder="e.g., What vegetarian dishes do you have?")

        with gr.Row():
            send_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear")
            confirm_btn = gr.Button("Confirm")

        send_btn.click(chat_handler, inputs=[message_box, chatbot], outputs=[chatbot, message_box])
        message_box.submit(chat_handler, inputs=[message_box, chatbot], outputs=[chatbot, message_box])

        clear_btn.click(lambda: [], outputs=chatbot, queue=False)
        confirm_btn.click(manager_confirmation, inputs=chatbot, outputs=chatbot, queue=False)

        gr.Examples(
            examples=[
                "What are your opening hours?",
                "What spicy dishes are available?",
                "What is your phone number and address?",
                "Table for 2 people on 16.05.2026 at 19:00, name is Sara",
                "Cancel reservation 3"],
            inputs=message_box,
        )

    return demo

def main() -> None:
    bot = create_bot()
    demo = build_demo(bot)
    # Use port 7861 to avoid conflict with rag_pdf.py which runs on 7860.
    demo.launch(server_port=7861)

if __name__ == "__main__":
    main()

