import os
from typing import List
import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from dal_rst_telegram import (get_restaurant_details_and_hours,
                     search_menu_items,
                     pend_reservation,
                     pend_cancellation,
                     get_reservation_details_by_id,
                     update_pending_reservations,
                     validate)

from n8n_interact import (N8nNotify,
                          GetResponse,
                          #test_post_data_url,
                          public_get_data_url,
                          #test_get_data_url,
                          public_post_data_url)

from docker_ollama import create_local_llm



class RestaurantTelegramChatbot:
    """RAG-style restaurant assistant backed by SQLite tables."""

    def __init__(self, db_path: str, model_name: str = "gpt-4o-mini") -> None:
        self.db_path = db_path
        self.llm = None
        self.llm_name = ""

        # If an API key exists, use OpenAI through LangChain.
        if os.getenv("OPENAI_API_KEY"):
            self.llm = ChatOpenAI(model=model_name, temperature=0)
            self.llm_name = "openai"
        else:
            self.llm = create_local_llm()
            self.llm_name = "ollama"

        # Answer prompt consumes retrieved SQL context and forms a final reply.
        self.answer_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful restaurant assistant. Use only the provided context.\n"
                    "If context does not contain the answer, say you are not sure and ask a clarifying question.\n"
                    "Never ask which restaurant the user means."
                ),
                ("human", "Question: {question}\n\nContext:\n{context}"),
            ]
        )

    @staticmethod
    def format_history(history):
        if not history:
            return ""
        return "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in history
        )

    def classify_question(self, question: str) -> str:
        """Use the LLM to classify the user's intent."""
        if not self.llm:
            return "general"

        classify_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a router for a restaurant chatbot. "
             "Classify the user message into exactly one of these categories:\n"
             "  reservation   — user wants to book a table\n"
             "  cancellation  — user wants to cancel an existing booking\n"
             "  menu          — questions about food, drinks, or prices\n"
             "  hours         — questions about opening hours or location\n"
             "  details       — questions about details of the restaurant\n"
             "  general       — anything else\n"
             "Return ONLY the single category word. No punctuation, no explanation."),
            ("human", "{question}")
        ])

        chain = classify_prompt | self.llm | StrOutputParser()
        result = chain.invoke({"question": question}).strip().lower()

        print("route", result)
        valid = {"reservation", "cancellation", "menu", "hours","details","general"}
        return result if result in valid else "general"

    def _build_menu_context(self, question: str) -> tuple[str, bool]:
        rows = search_menu_items(self.db_path, question)
        if not rows:
            return "No menu records matched the question.", False

        lines: List[str] = []
        for row in rows:
            veg = "vegetarian" if row["is_vegetarian"] else "non-vegetarian"
            spicy = "spicy" if row["is_spicy"] else "not spicy"
            status = "available" if row["is_available"] else "currently unavailable"
            lines.append(
                f"- {row['item_name']} ({row['category']}): {row['description']} | "
                f"${row['price']:.2f} | {veg}, {spicy}, {status}"
            )
        return "\n".join(lines), True

    def _build_details_context(self) -> str:
        details, hours = get_restaurant_details_and_hours(self.db_path)
        if not details:
            return "No restaurant details found."

        details_text = (
            f"Name: {details['name']}\n"
            f"Address: {details['address']}\n"
            f"Phone: {details['phone']}\n"
            f"Email: {details['email']}\n"
            f"Website: {details['website']}"
        )

        hours_lines = [
            f"- {h['day_of_week']}: {h['open_time']} to {h['close_time']}"
            + (f" ({h['notes']})" if h.get("notes") else "")
            for h in hours
        ]
        return details_text + "\n\nOpening Hours:\n" + "\n".join(hours_lines)

    def _handle_reservation(self, question: str,history:str)->str:
        self.confirm_events()

        # Ask the LLM to extract structured data from the user's message
        extract_prompt = ChatPromptTemplate.from_messages([(
        "system","You are professional assistant that extract the required details,\nAnd using context as chat history\n\n"
        "Extract details:"
        "  customer_name : str type, name of the customer,\n"
        "  date : extract in format: '00.00.0000' (d.m.y) ,\n"
        "  time : extract in format: '00:00' ,\n"
        "  party_size : integer type, people count on reservation.\n\n"
        "your output should be as JSON type no any other details but - 'key':'value'.\n"
        "if some field does not mentioned, fill it with null instead.\n"
        "Answer the question with help if needed from the context,\n"

        ),
        ("human","Question: {question}\n\nContext:{context}")
         ])

        if not self.llm:
            return "Please call us directly to make a reservation!"

        if self.llm_name == "ollama":
            reservation_llm_json_format = self.llm.bind(format="json")
            chain = extract_prompt | reservation_llm_json_format | StrOutputParser()
        else:
            chain = extract_prompt | self.llm | StrOutputParser()

        raw = chain.invoke({"question": question,"context":history})

        try:
            details = json.loads(raw)
            missing = validate(details)
            if len(missing) > 0:
                m_missing = ", ".join(m for m in missing)
                return (f"Your:   **{m_missing}**   is missing  "
                        f"Example: 'Table for 2 people on 16.05.2026 at 19:00, name is Sara'")

            res_id = pend_reservation(
                self.db_path,
                details["customer_name"], details["date"],
                str(details["time"]), int(details["party_size"]),
                details.get("contact")
            )

            if not res_id:
                return ("Sorry, Process failed,\n"
                        "please write like the Example: 'Table for 2 people on 16.05.2026 at 19:00, name is Sara'")


            n8n = N8nNotify(booking_id=res_id,name=details["customer_name"],date=details["date"],time=details["time"],status="pending",webhook_url=public_post_data_url)
            if not n8n.notify_n8n():
                print("N8N Notify Failed.")

            return (f"send a message to https://t.me/stFirstBot to confirm your reservation.\n"
                    f"After confirm on telegram to be sure you registered come back here,\n"
                    f"And press the Confirm button for absolute confirmation!\n"
                    f"booking_id:    {res_id}\n"
                    f"your name:     {details["customer_name"]}\n"
                    f"your date:     {details["date"]}\n"
                    f"your time:      {details["time"]}\n"
                    f"event:         reservation")

        except (json.JSONDecodeError, ValueError):
            return ("Sorry, Process failed,\n"
                    "The bot should answer for relevant questions about our restaurant.\n"
                    "for reservation write like the Example:\n'Table for 2 people on 16.05.2026 at 19:00, name is Sara'")

    def _handle_cancellation(self, question: str,history:str):
        # Simple: ask the user for their booking ID
        # (For the bonus: use LLM to extract booking ID from the message)
        self.confirm_events()

        match = re.search(r'\b(\d+)\b', question)

        if match:
            res_id = int(match.group(1))
            cancel_rowcount = pend_cancellation(db_path=self.db_path, reservation_id=res_id)

            if not cancel_rowcount:
                return "Sorry, I couldn't process that. Please try again.(make sure you mention reservation ID)"

            details = get_reservation_details_by_id(db_path=self.db_path, reservation_id=res_id)

            n8n = N8nNotify(booking_id=res_id, name=details["customer_name"], date=details["date"],time=details["time"], status="pending_to_cancel",webhook_url=public_post_data_url)
            if not n8n.notify_n8n():
                print("N8N Notify Failed.")

            return ("send a message to https://t.me/stFirstBot to confirm your cancellation\n"
                    f"booking_id: {res_id}\n"
                    f"your name: {details["customer_name"]}\n"
                    f"event: cancellation")


        else:
            extract_cancellation_id_prompt = ChatPromptTemplate([
                ("system",
                 "Extract ONLY a numeric id. Return digits only. If none, return empty string."),
                ("human","{question}")
            ])

            chain = extract_cancellation_id_prompt | self.llm| StrOutputParser()
            match_llm = chain.invoke({"question": question})

            if str(match_llm).isdigit():
                res_id = int(match_llm)
                cancel_rowcount = pend_cancellation(self.db_path, res_id)

                if not cancel_rowcount:
                    return "Sorry, I couldn't process that. Please try again.(make sure you mention reservation ID)"

                details = get_reservation_details_by_id(db_path=self.db_path, reservation_id=res_id)

                n8n = N8nNotify(booking_id=res_id, name=details["customer_name"], date=details["date"],
                                time=details["time"], status="pending_to_cancel",webhook_url=public_post_data_url)
                if not n8n.notify_n8n():
                    print("N8N Notify Failed.")

                return ("send a message to https://t.me/stFirstBot to confirm your cancellation\n"
                        f"booking_id: {res_id}\n"
                        f"your name: {details["customer_name"]}\n"
                        f"event: cancellation")

        return "Sorry, I couldn't process that. Please try again.(make sure reservation ID mentioned)"

    def confirm_events(self):
        events_ids = GetResponse(public_get_data_url)
        events_ids_json = events_ids.get_response()
        row_count = 0

        if events_ids_json is not None:
            for i in events_ids_json:
                row_count += update_pending_reservations(self.db_path, reservation_id=i["booking_id"],
                                                             event=i["event"])

        print(f"Confirmed Rows: {row_count}")
        return row_count

    def answer(self, question: str,history:list) -> str:
        """Route question, retrieve matching SQLite data, and generate an answer."""
        route = self.classify_question(question)

        if route == "menu":
            context, has_match = self._build_menu_context(question)

            if not has_match:
                return (
                    "I could not find that item in the current menu.\n"
                    "Ask me to list available mains, starters, desserts, or drinks."
                )

        elif route in ["details","hours"]:
            context = self._build_details_context()

        elif route == "reservation":
            return self._handle_reservation(question,self.format_history(history))

        elif route == "cancellation":
            return self._handle_cancellation(question,self.format_history(history))

        else:
            return (
                f"I can help with menu items, prices, ingredients, and restaurant details\n"
                "like opening hours, phone, address, and making reservations(also cancel)."
            )

        # Without OpenAI, return context directly so the app is still functional.
        if not self.llm:
            return f"(Local fallback, no OpenAI key configured)\n{context}"

        chain = self.answer_prompt | self.llm | StrOutputParser()
        return chain.invoke({"question": question, "context": context})

