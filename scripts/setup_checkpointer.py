from app.memory.checkpointer import (
    create_checkpointer,
)


def main():
    with create_checkpointer() as checkpointer:
        checkpointer.setup()

    print(
        "LangGraph checkpoint storage initialized."
    )


if __name__ == "__main__":
    main()