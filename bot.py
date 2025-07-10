import asyncio
from typing import Optional, List
from datetime import datetime
import platform

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, select
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence
from langchain_community.llms import FakeListLLM  # For testing
from pydantic import BaseModel

# --- Database Models ---
class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# --- Pydantic Models ---
class TaskCreate(BaseModel):
    description: str

class TaskUpdate(BaseModel):
    description: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    description: str
    created_at: datetime

# --- Repository Layer ---
class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, task: TaskCreate) -> TaskResponse:
        db_task = Task(user_id=user_id, description=task.description)
        self.session.add(db_task)
        await self.session.commit()
        await self.session.refresh(db_task)
        return TaskResponse(id=db_task.id, description=db_task.description, created_at=db_task.created_at)

    async def read(self, user_id: int, task_id: int) -> Optional[TaskResponse]:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task:
            return TaskResponse(id=task.id, description=task.description, created_at=task.created_at)
        return None

    async def update(self, user_id: int, task_id: int, task: TaskUpdate) -> Optional[TaskResponse]:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        db_task = result.scalar_one_or_none()
        if db_task:
            if task.description:
                db_task.description = task.description
            await self.session.commit()
            await self.session.refresh(db_task)
            return TaskResponse(id=db_task.id, description=db_task.description, created_at=db_task.created_at)
        return None

    async def delete(self, user_id: int, task_id: int) -> bool:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task:
            await self.session.delete(task)
            await self.session.commit()
            return True
        return False

    async def list(self, user_id: int) -> List[TaskResponse]:
        result = await self.session.execute(
            select(Task).where(Task.user_id == user_id)
        )
        tasks = result.scalars().all()
        return [TaskResponse(id=t.id, description=t.description, created_at=t.created_at) for t in tasks]

# --- Analyzer Layer ---
class TaskAnalyzer:
    def __init__(self):
        self.llm = FakeListLLM(responses=[
            'Action: create, Description: "Buy groceries"',
            'Action: list',
            'Action: update, ID: 1, Description: "Buy groceries and milk"',
            'Action: delete, ID: 1'
        ])
        self.prompt = PromptTemplate.from_template(
            "Determine action (create, read, update, delete, list) and relevant details: {input}"
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

    def analyze(self, user_input: str) -> dict:
        result = self.chain.invoke({"input": user_input})
        action = None
        details = {}
        for part in result.split(","):
            if "Action:" in part:
                action = part.split(":")[1].strip()
            elif "Description:" in part:
                details["description"] = part.split("Description:")[1].strip().strip('"')
            elif "ID:" in part:
                details["id"] = int(part.split("ID:")[1].strip())
        return {"action": action, **details}

# --- Service Layer ---
class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    async def handle_action(self, user_id: int, analysis: dict) -> str:
        action = analysis.get("action")
        if action == "create":
            task = TaskCreate(description=analysis["description"])
            result = await self.repository.create(user_id, task)
            return f"✅ Task created: {result.description} (ID: {result.id})"
        elif action == "read":
            task = await self.repository.read(user_id, analysis["id"])
            return f"📄 Task: {task.description} (ID: {task.id})" if task else "❌ Task not found"
        elif action == "update":
            task = TaskUpdate(description=analysis.get("description"))
            result = await self.repository.update(user_id, analysis["id"], task)
            return f"✏️ Task updated: {result.description} (ID: {result.id})" if result else "❌ Task not found"
        elif action == "delete":
            success = await self.repository.delete(user_id, analysis["id"])
            return "🗑 Task deleted" if success else "❌ Task not found"
        elif action == "list":
            tasks = await self.repository.list(user_id)
            if not tasks:
                return "📭 No tasks found"
            return "\n".join(f"📝 ID: {t.id}, Description: {t.description}" for t in tasks)
        return "❌ Invalid action"

# --- UI Keyboard ---
def create_main_keyboard():
    buttons = [
        [KeyboardButton(text="➕ Add Task"), KeyboardButton(text="📋 List Tasks")],
        [KeyboardButton(text="✏ Update Task"), KeyboardButton(text="🗑 Delete Task")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- Bot Layer ---
class TaskBot:
    def __init__(self, token: str, repository: TaskRepository, analyzer: TaskAnalyzer):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.service = TaskService(repository)
        self.analyzer = analyzer
        self._register_handlers()

    def _register_handlers(self):
        @self.dp.message(Command("start"))
        async def start_command(message: types.Message):
            await message.answer(
                "👋 Welcome to the Task Bot!\nChoose an action or type a task description.",
                reply_markup=create_main_keyboard()
            )

        @self.dp.message()
        async def handle_message(message: types.Message):
            user_input = message.text.strip()
            emoji_map = {
                "➕ Add Task": "create task: Buy groceries",
                "📋 List Tasks": "list tasks",
                "✏ Update Task": "update task ID: 1, Description: Buy eggs",
                "🗑 Delete Task": "delete task ID: 1"
            }
            interpreted_input = emoji_map.get(user_input, user_input)
            analysis = self.analyzer.analyze(interpreted_input)
            response = await self.service.handle_action(message.from_user.id, analysis)
            await message.answer(response, reply_markup=create_main_keyboard())

    async def start(self):
        await self.dp.start_polling(self.bot)

# --- Main ---
async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    repository = TaskRepository(session)
    analyzer = TaskAnalyzer()
    bot = TaskBot("YOUR_TELEGRAM_BOT_TOKEN", repository, analyzer)
    await bot.start()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())

