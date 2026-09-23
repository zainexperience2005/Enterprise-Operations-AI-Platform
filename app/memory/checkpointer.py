from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings


def create_checkpointer():
    return PostgresSaver.from_conn_string(
        settings.checkpoint_database_url
    )