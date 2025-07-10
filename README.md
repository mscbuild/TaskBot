# TaskBot: A Telegram Task Management Bot

## Overview

TaskBot is a Telegram bot built with Python 3.12, aiogram, SQLAlchemy, and LangChain. It allows users to manage tasks (create, read, update, delete, and list) using natural language, with LLM-driven intent analysis. The architecture follows a layered approach (router -> analysis -> processing -> response) with strict CRUD separation, memory-layer abstraction, and access control.

## Features

- Create, read, update, delete, and list tasks via Telegram commands or natural language.
- LLM-driven intent analysis using LangChain for processing user input.
- Strict CRUD operations with SQLAlchemy for database interactions.
- User-specific access control to ensure data privacy.
- Type-safe code with Pydantic models and Python 3.12 type hints.
- Asynchronous operations for scalability using aiogram and async SQLAlchemy.
- Minimal unit tests with pytest for core functionality.

## Project Structure

```
taskbot/
├── bot.py           # Main bot code (router, analysis, processing, repository, tests)
├── README.md       # Project documentation
└── requirements.txt # Project dependencies
```

- **Router**: Handles Telegram messages using aiogram.
- **Analysis**: Uses LangChain to parse user intent (e.g., "create task: buy groceries").
- **Processing**: Executes business logic with strict separation of concerns.
- **Memory Layer**: Abstracts database operations using SQLAlchemy.
- **Access Control**: Ensures users can only access their own tasks.

## Requirements

- Python 3.12+
- Telegram Bot Token (obtain from [BotFather](https://t.me/BotFather))
- Dependencies (listed in `requirements.txt`):
  - aiogram
  - sqlalchemy[asyncio]
  - langchain
  - langchain-community
  - pydantic
  - pytest
  - pytest-asyncio

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd taskbot
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Bot**:
   - Replace `"YOUR_BOT_TOKEN"` in `bot.py` with your Telegram bot token.
   - (Optional) Replace the `FakeListLLM` in `bot.py` with a real LLM (e.g., OpenAI or HuggingFace) for production use. Configure API keys as needed.

4. **Set Up the Database**:
   - The bot uses an in-memory SQLite database by default (`sqlite+aiosqlite:///:memory:`).
   - For production, update the database URL in `bot.py` to use a persistent database (e.g., PostgreSQL: `postgresql+asyncpg://user:password@localhost/dbname`).

5. **Run the Bot**:
   ```bash
   python bot.py
   ```

## Usage

1. Start the bot by sending `/start` in Telegram.
2. Send natural language commands, e.g.:
   - "Create a task: Buy groceries"
   - "List my tasks"
   - "Update task 1: Buy groceries and milk"
   - "Delete task 1"
   - "Show task 1"
3. The bot will respond with the result of the action (e.g., "Task created: Buy groceries (ID: 1)").

## Testing

Run unit tests to verify CRUD operations:
```bash
pytest bot.py
```

The tests cover:
- Creating a task
- Reading a task
- Updating a task
- Listing tasks
- Deleting a task

## Extending the Bot

- **Custom LLM**: Replace `FakeListLLM` with a production-ready LLM (e.g., `langchain_openai.OpenAI`) and configure API keys.
- **Database**: Switch to a persistent database like PostgreSQL for production.
- **Additional Features**: Extend the `TaskAnalyzer` to support more complex intents or add new commands in `TaskBot`.

## Notes

- The bot uses an in-memory database for simplicity. For production, use a persistent database to retain data.
- Ensure your Telegram bot token is kept secure and not exposed in version control.
- The `FakeListLLM` is used for testing. For real-world use, integrate a proper LLM and handle rate limits or errors.

## License

MIT License
