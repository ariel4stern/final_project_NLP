import sqlite3
from typing import Any, Dict, List, Tuple, cast
from contextlib import contextmanager

DB_PATH = "restaurant.sqlite"

@contextmanager
def get_connection(db_path:str):

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()

    except sqlite3.OperationalError as e:
        raise RuntimeError(f"DB connection failed: {e}")

    finally:
        conn.close()

def create_table_reservations(db_path:str) -> None:
    query = """
    CREATE TABLE IF NOT EXISTS reservations (
        booking_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        date          TEXT NOT NULL,
        time          TEXT NOT NULL,
        party_size    INTEGER NOT NULL,
        contact       TEXT,
        status        TEXT NOT NULL DEFAULT 'pending',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """

    try:
        with get_connection(db_path) as conn:
            conn.execute(query)

    except Exception as e:
        raise RuntimeError("Failed to create reservations table") from e

def pend_reservation(db_path: str, customer_name: str, date: str,time: str, party_size: int, contact: str = None)->int|None:
    query = """INSERT INTO reservations
            (customer_name, date, time, party_size, contact)
            VALUES (?, ?, ?, ?, ?)
             """


    with get_connection(db_path) as conn:
        cursor = conn.execute(query, (customer_name, date, time, party_size,
                                                contact))

        if not cursor.lastrowid:
            return None

        return cursor.lastrowid
def pend_cancellation(db_path: str, reservation_id: int)->int|None:
    res_for_update = get_reservation_details_by_id(db_path, reservation_id)
    if res_for_update is None:
        return None

    query = """UPDATE reservations 
            SET status = ?
            WHERE booking_id = ?
            AND status = 'confirmed'"""

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, ('pending_to_cancel',reservation_id,))

        if cursor.rowcount == 0:
            print("Not such row to update")
            return None

        return cursor.rowcount
def update_pending_reservations(db_path: str, reservation_id: int,event:str)->int|None:
    valid_changes = {
        "pending": ["confirmed"],
        "pending_to_cancel": ["cancelled"],
        "confirmed": [],
        "cancelled": []
    }
    select_query = """SELECT status FROM reservations WHERE booking_id = ?"""
    update_query = """UPDATE reservations SET status = ? WHERE booking_id = ?"""
    with get_connection(db_path) as conn:
        row = conn.execute(select_query, (reservation_id,)).fetchone()

        if not row:
            return 0

        current_status = row[0]

        if event not in valid_changes.get(current_status,[]):
            return 0

        cursor = conn.execute( update_query, (event, reservation_id))

        if cursor.rowcount == 0:
            return 0

        return 1

def get_reservation_details_by_id(db_path: str, reservation_id: int) -> Dict[str,Any] | None:
    query = """SELECT * FROM reservations WHERE booking_id = ?"""


    with get_connection(db_path) as conn:
        row = conn.execute(query, (reservation_id,)).fetchone()

        if not row:
            print("ID Not Found")
            return None

        return dict(row)

def initialize_database(db_path: str = DB_PATH) -> None:
    """Create tables and seed starter data if this is a new database."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                is_vegetarian INTEGER NOT NULL DEFAULT 0,
                is_spicy INTEGER NOT NULL DEFAULT 0,
                is_available INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurant_details (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                website TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opening_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week TEXT NOT NULL UNIQUE,
                open_time TEXT NOT NULL,
                close_time TEXT NOT NULL,
                notes TEXT
            )
            """
        )

        create_table_reservations(db_path="restaurant.sqlite")
        _seed_if_empty(conn)
def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Insert a small demo dataset once, keeping reruns idempotent."""
    has_menu = conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] > 0
    has_details = conn.execute("SELECT COUNT(*) FROM restaurant_details").fetchone()[0] > 0
    has_hours = conn.execute("SELECT COUNT(*) FROM opening_hours").fetchone()[0] > 0

    if not has_menu:
        menu_rows = [
            ("Margherita Pizza", "Main", "Tomato, mozzarella, basil", 10.50, 1, 0, 1),
            ("Spicy Chicken Burger", "Main", "Grilled chicken, jalapeno mayo", 11.90, 0, 1, 1),
            ("Caesar Salad", "Starter", "Romaine, parmesan, croutons", 7.25, 0, 0, 1),
            ("Mushroom Risotto", "Main", "Creamy arborio rice with mushrooms", 12.75, 1, 0, 1),
            ("Lemon Tart", "Dessert", "House-made tart with lemon curd", 5.20, 1, 0, 1),
            ("Iced Latte", "Drinks", "Espresso with cold milk and ice", 4.60, 1, 0, 1),
        ]
        conn.executemany(
            """
            INSERT INTO menu_items
            (item_name, category, description, price, is_vegetarian, is_spicy, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            menu_rows,
        )

    if not has_details:
        conn.execute(
            """
            INSERT INTO restaurant_details (id, name, address, phone, email, website)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                "Sunset Bistro",
                "123 Market Street, Springfield",
                "+1-555-0142",
                "hello@sunsetbistro.example",
                "www.sunsetbistro.example",
            ),
        )

    if not has_hours:
        hours_rows = [
            ("Monday", "09:00", "21:00", ""),
            ("Tuesday", "09:00", "21:00", ""),
            ("Wednesday", "09:00", "21:00", ""),
            ("Thursday", "09:00", "22:00", ""),
            ("Friday", "09:00", "23:00", ""),
            ("Saturday", "10:00", "23:00", "Brunch menu until 14:00"),
            ("Sunday", "10:00", "20:00", "Family set menu available"),
        ]
        conn.executemany(
            """
            INSERT INTO opening_hours (day_of_week, open_time, close_time, notes)
            VALUES (?, ?, ?, ?)
            """,
            hours_rows,
        )

def get_menu_items(db_path: str) -> List[Dict[str, Any]] | None:
    """Return all menu rows as dictionaries."""
    select_query = """SELECT item_name,
                             category,
                             description,
                             price,
                             is_vegetarian,
                             is_spicy,
                             is_available
            FROM menu_items
            ORDER BY category, item_name"""

    with get_connection(db_path) as conn:

        rows = conn.execute(select_query).fetchall()

        if not rows:
            print("No menu items found")
            return None

        return [cast(Dict[str, Any], dict(row)) for row in rows]
def search_menu_items(db_path: str, query: str) -> List[Dict[str, Any]] | None:
    """Simple LIKE-based search used to fetch only relevant menu rows."""
    menu_items = get_menu_items(db_path)
    if menu_items is None:
        return None

    tokens = [t.strip().lower() for t in query.split() if len(t.strip()) >= 3]
    if not tokens:
        return menu_items

    where_clauses = []
    params: List[str] = []
    for token in tokens[:10]:
        where_clauses.append("(LOWER(item_name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)")
        wildcard = f"%{token}%"
        params.extend([wildcard, wildcard, wildcard])

    sql = (
        "SELECT item_name, category, description, price, is_vegetarian, is_spicy, is_available "
        "FROM menu_items WHERE " + " OR ".join(where_clauses) + " ORDER BY category, item_name"
    )

    print("len params :-: " ,len(params))
    print("sql :-: ",sql)

    with get_connection(db_path) as conn:
        rows = conn.execute(sql,params).fetchall()
        if not rows:
            return menu_items
        return [cast(Dict[str, Any], dict(row)) for row in rows]
def get_restaurant_details_and_hours(db_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Return one restaurant details row and all opening-hours rows."""

    details_select_query = """SELECT name, address, phone, email, website FROM restaurant_details WHERE id = 1"""
    hours_select_query = """SELECT day_of_week, open_time, close_time, notes FROM opening_hours ORDER BY id"""

    with get_connection(db_path) as conn:
        details_row = conn.execute(details_select_query).fetchone()
        hours_rows = conn.execute(hours_select_query).fetchall()
        details = cast(Dict[str, Any], dict(details_row)) if details_row else {}
        hours = [cast(Dict[str, Any], dict(row)) for row in hours_rows]
        return details, hours
def validate(details:dict)->List[str]:
    missing = []

    if not details.get("customer_name"):
        missing.append("name")
    if not details.get("date"):
        missing.append("date")
    if not details.get("time"):
        missing.append("time")
    if details.get("party_size") is None:
        missing.append("party size")

    return missing

# Extra function remove if no need
def get_all_reservations(db_path: str) -> List[Dict[str, Any]] | None:
    query = """SELECT * FROM reservations"""

    with get_connection(db_path) as conn:
        rows = conn.execute(query).fetchall()

        if not rows:
            print("Not Reservations Found")
            return None

        return [dict(r) for r in rows]
def get_all_pending_reservations(db_path: str) -> List[Dict[str, Any]] | None:
    query = """SELECT booking_id, status FROM reservations
                WHERE status = 'pending' OR status = 'pending_to_cancel'
                """

    with get_connection(db_path) as conn:
        rows = conn.execute(query).fetchall()
        if not rows:
            return None
        return [dict(r) for r in rows]

def remove_reservations_by_event(db_path: str,event:str=None)->int:
    query = """DELETE FROM reservations WHERE status = ?"""


    with get_connection(db_path) as conn:
        d_counter = 0
        if event is None:
            p_cursor = conn.execute(query, ("pending",))
            if p_cursor.rowcount == 0:
                return 0
            d_counter += p_cursor.rowcount

            p_c_cursor = conn.execute(query, ("pending_to_cancel",))
            if p_c_cursor.rowcount == 0:
                return 0

            return d_counter+p_c_cursor.rowcount

        else:
            s_cursor = conn.execute(query,(event,))
            if s_cursor.rowcount == 0:
                return 0

            return d_counter + s_cursor.rowcount
def delete_reservations(db_path: str)-> int|None:
    query = """DELETE FROM reservations"""

    with get_connection(db_path) as conn:
        cursor = conn.execute(query)

        if cursor.rowcount == 0:
            return  0

        return cursor.rowcount
def delete_reservations_new_ids(db_path: str)->int|None:
    regular_query = """DELETE FROM reservations"""
    permanent_query = """DELETE FROM sqlite_sequence WHERE name='reservations'
            """

    with get_connection(db_path) as conn:
        d_counter=0
        r_cursor = conn.execute(regular_query)
        if r_cursor.rowcount == 0:
            return 0

        p_cursor = conn.execute(permanent_query)
        if p_cursor.rowcount == 0:
            return 0

        return d_counter + p_cursor.rowcount    #to know how much deleted permanent








