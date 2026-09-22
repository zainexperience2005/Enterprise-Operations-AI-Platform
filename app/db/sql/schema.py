from sqlalchemy import inspect

from app.db.session import readonly_engine


ALLOWED_TABLES = {
    "customers",
    "orders",
    "order_items",
    "invoices",
    "payments",
    "support_tickets",
}


def get_database_schema() -> dict:
    inspector = inspect(readonly_engine)

    schema = {}

    for table_name in sorted(ALLOWED_TABLES):
        columns = inspector.get_columns(table_name)

        schema[table_name] = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
            }
            for column in columns
        ]

    return schema