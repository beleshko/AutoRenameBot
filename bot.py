elif data == "use_current":#!/usr/bin/env python3
"""
AUTONICK S
Telegram-бот для автоматической смены ника 

Установка:
pip install telethon

Запуск:
python3 bot.py
"""

import asyncio
import json
import logging
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.errors import FloodWaitError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('autonick_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================================
# КОНФИГУРАЦИЯ СЕРВИСА
# ========================================

SERVICE_CONFIG = {
    'api_id': None,  # Укажите API ID сервиса
    'api_hash': None,  # Укажите API Hash сервиса
    'bot_token': None,  # Укажите токен бота
}


class SafetyManager:
    """Менеджер безопасности"""
    
    def __init__(self):
        self.change_history: List[float] = []
        self.flood_wait_until: Optional[float] = None
        self.daily_changes = 0
        self.last_reset = datetime.now()
        
        self.HOURLY_LIMIT = 25
        self.DAILY_LIMIT = 400
        self.MIN_INTERVAL = 95
        self.MAX_INTERVAL = 175
        
    def can_change_nick(self) -> tuple[bool, str]:
        now = time.time()
        
        if datetime.now() - self.last_reset > timedelta(days=1):
            self.daily_changes = 0
            self.last_reset = datetime.now()
        
        if self.flood_wait_until and now < self.flood_wait_until:
            wait_time = int(self.flood_wait_until - now)
            return False, f"FloodWait: {wait_time}с"
        
        if self.daily_changes >= self.DAILY_LIMIT:
            return False, f"Дневной лимит достигнут"
        
        hour_ago = now - 3600
        recent = [t for t in self.change_history if t > hour_ago]
        if len(recent) >= self.HOURLY_LIMIT:
            return False, f"Часовой лимит достигнут"
        
        if self.change_history:
            if now - self.change_history[-1] < self.MIN_INTERVAL:
                return False, "Слишком частая смена"
        
        return True, "OK"
    
    def register_change(self):
        now = time.time()
        self.change_history.append(now)
        self.daily_changes += 1
        hour_ago = now - 3600
        self.change_history = [t for t in self.change_history if t > hour_ago]
    
    def set_flood_wait(self, seconds: int):
        self.flood_wait_until = time.time() + seconds
    
    def get_optimal_delay(self) -> float:
        base = random.uniform(self.MIN_INTERVAL, self.MAX_INTERVAL)
        hour_ago = time.time() - 3600
        recent = [t for t in self.change_history if t > hour_ago]
        
        if len(recent) > 20:
            base *= 1.5
        elif len(recent) > 15:
            base *= 1.2
        
        return base
    
    def get_stats(self) -> str:
        now = time.time()
        hour_ago = now - 3600
        recent = [t for t in self.change_history if t > hour_ago]
        
        return (
            f"📊 Статистика:\n"
            f"├ За час: {len(recent)}/{self.HOURLY_LIMIT}\n"
            f"├ За день: {self.daily_changes}/{self.DAILY_LIMIT}\n"
            f"└ FloodWait: {'⚠️ Да' if self.flood_wait_until and self.flood_wait_until > now else '✅ Нет'}"
        )


class NameVariantsGenerator:
    """Генератор вариантов имени"""
    
    @staticmethod
    def generate_from_base(base_name: str) -> List[str]:
        """Генерация вариантов на основе имени пользователя"""
        if not base_name or len(base_name) > 30:
            return []
        
        variants = [base_name]
        
        # Символы вокруг
        symbols = [
            ("»", "«"), ("«", "»"), ("‹", "›"), ("│", "│"),
            ("║", "║"), ("┃", "┃"), ("•", "•"), ("◦", "◦"),
            ("⚡", "⚡"), ("✦", "✦"), ("✧", "✧"), ("♛", "♛"),
            ("【", "】"), ("〖", "〗"), ("⟨", "⟩"), ("⟪", "⟫"),
            ("▞", "▚"), ("▣", "▣"), ("◈", "◈"), ("∞", "∞"),
            ("∆", "∆"), ("⌬", "⌬"), ("▁", "▁"), ("▂", "▂"),
        ]
        
        for left, right in symbols:
            variants.append(f"{left}{base_name}{right}")
            variants.append(f"{left} {base_name} {right}")
        
        # С разделителями
        separators = ["•", "◦", "›", "→", "⟡", "◈", "⚡", "✦", "|"]
        for sep in separators:
            variants.append(f"{base_name} {sep}")
            variants.append(f"{sep} {base_name}")
            variants.append(f"{sep} {base_name} {sep}")
        
        # Стилизация
        variants.extend([
            f"〘{base_name}〙",
            f"⎡{base_name}⎤",
            f"⎣{base_name}⎦",
            f"『{base_name}』",
            f"「{base_name}」",
            f"꧁{base_name}꧂",
            f"━ {base_name} ━",
            f"═ {base_name} ═",
            f"▪️ {base_name} ▪️",
            f"▫️ {base_name} ▫️",
        ])
        
        # Фильтрация по длине
        return [v[:64] for v in variants if len(v) <= 64]
    
    @staticmethod
    def get_style_presets(base_name: str) -> List[str]:
        """Стильные пресеты на основе имени пользователя"""
        if not base_name or len(base_name) > 30:
            return []
        
        variants = []
        
        # Базовые вариации
        variants.extend([
            base_name,
            base_name.upper(),
            base_name.lower(),
            base_name.title(),
        ])
        
        # С символами вокруг (расширенный набор)
        symbols = [
            ("»", "«"), ("«", "»"), ("‹", "›"), ("›", "‹"),
            ("│", "│"), ("║", "║"), ("┃", "┃"),
            ("•", "•"), ("◦", "◦"), ("▪", "▪"), ("▫", "▫"),
            ("⚡", "⚡"), ("✦", "✦"), ("✧", "✧"), ("✨", "✨"),
            ("♛", "♛"), ("♔", "♔"), ("♕", "♕"),
            ("【", "】"), ("〖", "〗"), ("『", "』"), ("「", "」"),
            ("⟨", "⟩"), ("⟪", "⟫"), ("⦑", "⦒"), ("⧼", "⧽"),
            ("▞", "▚"), ("▣", "▣"), ("◈", "◈"), ("◉", "◉"),
            ("∞", "∞"), ("∆", "∆"), ("⌬", "⌬"),
            ("꧁", "꧂"), ("༺", "༻"), ("⎡", "⎤"), ("⎣", "⎦"),
        ]
        
        for left, right in symbols:
            variants.append(f"{left}{base_name}{right}")
            variants.append(f"{left} {base_name} {right}")
        
        # С разделителями и префиксами
        separators = ["•", "◦", "›", "→", "⟡", "◈", "⚡", "✦", "✧", "▪", "▫", "|", "//", "~"]
        for sep in separators:
            variants.extend([
                f"{base_name} {sep}",
                f"{sep} {base_name}",
                f"{sep} {base_name} {sep}",
            ])
        
        # Стилизованные рамки
        variants.extend([
            f"━━ {base_name} ━━",
            f"═══ {base_name} ═══",
            f"▬▬ {base_name} ▬▬",
            f"┏━ {base_name} ━┓",
            f"┗━ {base_name} ━┛",
            f"╔═ {base_name} ═╗",
            f"╚═ {base_name} ═╝",
        ])
        
        # Точки и пробелы между буквами
        spaced = " ".join(base_name)
        variants.extend([
            spaced,
            "·".join(base_name),
            " • ".join(base_name),
        ])
        
        # Уникальные стили
        variants.extend([
            f"〘{base_name}〙",
            f"⎡{base_name}⎤",
            f"⎣{base_name}⎦",
            f"⎧{base_name}⎫",
            f"⎨{base_name}⎬",
            f"⎩{base_name}⎭",
            f"『{base_name}』",
            f"「{base_name}」",
            f"꧁{base_name}꧂",
            f"༺{base_name}༻",
            f"⟨{base_name}⟩",
            f"⟪{base_name}⟫",
        ])
        
        # эмодзи
        emojis = ["⚡", "✨", "🔥", "💎", "⭐", "🌟", "✦", "✧", "◈", "◉", "♛", "♔"]
        for emoji in emojis[:6]:  # Берем первые 6
            variants.extend([
                f"{emoji} {base_name}",
                f"{base_name} {emoji}",
                f"{emoji} {base_name} {emoji}",
            ])
        
        # Фильтрация по длине и уникальность
        unique_variants = list(set([v[:64] for v in variants if len(v) <= 64]))
        return unique_variants


class UserSession:
    """Сессия пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.client: Optional[TelegramClient] = None
        self.safety = SafetyManager()
        self.original_name: Optional[str] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.variants: List[str] = []
        self.mode: str = 'preset'  # preset, custom, base
        self.custom_variants: List[str] = []


class AutoNickService:
   
    
    def __init__(self):
        self.bot_client: Optional[TelegramClient] = None
        self.sessions: Dict[int, UserSession] = {}
        self.data_dir = Path("user_data")
        self.data_dir.mkdir(exist_ok=True)
    
    async def start_bot(self):
        """Запуск бота"""
        if not SERVICE_CONFIG['bot_token']:
            print("❌ Укажите bot_token в SERVICE_CONFIG")
            return
        
        self.bot_client = TelegramClient(
            'autonick_bot',
            SERVICE_CONFIG['api_id'],
            SERVICE_CONFIG['api_hash']
        )
        
        await self.bot_client.start(bot_token=SERVICE_CONFIG['bot_token'])
        
        # Регистрация обработчиков
        self.bot_client.add_event_handler(self.handle_start, events.NewMessage(pattern='/start'))
        self.bot_client.add_event_handler(self.handle_callback, events.CallbackQuery())
        self.bot_client.add_event_handler(self.handle_message, events.NewMessage())
        
        logger.info("🚀 Бот запущен")
        print("✅ Бот готов к работе!")
        
        await self.bot_client.run_until_disconnected()
    
    def get_session(self, user_id: int) -> UserSession:
        """Получение или создание сессии"""
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]
    
    async def handle_start(self, event):
        """Обработка /start"""
        user_id = event.sender_id
        session = self.get_session(user_id)
        
        welcome_text = (
            "🎭 <b>GENTOOO AUTONICK SERVICE</b>\n\n"
            "Автоматическая смена ника с защитой от бана!\n\n"
            "🛡️ <b>Безопасность:</b>\n"
            "├ Лимиты: 25/час, 400/день\n"
            "├ Интервал: 95-175 сек\n"
            "└ Авто-обработка FloodWait\n\n"
            "Выберите режим работы:"
        )
        
        buttons = [
            [Button.inline("🎨 Стильные пресеты", b"mode_preset")],
            [Button.inline("📝 Свои варианты", b"mode_custom")],
            [Button.inline("🔤 Кастомная база", b"mode_base")],
            [Button.inline("ℹ️ Инструкция", b"help")],
        ]
        
        await event.respond(welcome_text, buttons=buttons, parse_mode='html')
    
    async def handle_callback(self, event):
        """Обработка нажатий кнопок"""
        user_id = event.sender_id
        session = self.get_session(user_id)
        data = event.data.decode()
        
        # Режимы работы
        if data == "mode_preset":
            session.mode = 'preset'
            
            # Подключаемся для получения текущего ника
            await event.edit("⏳ Подключение к вашему аккаунту...", buttons=None)
            
            if not await self.connect_user(session):
                await event.edit(
                    "❌ Ошибка подключения\n\n"
                    "Отправьте /start для повторной попытки",
                    buttons=[[Button.inline("◀️ Назад", b"menu")]]
                )
                return
            
            # Генерирация пресетов на основе текущего ника
            session.variants = NameVariantsGenerator.get_style_presets(session.original_name)
            
            if not session.variants:
                await event.edit(
                    "❌ Не удалось создать пресеты\n\n"
                    "Попробуйте другой режим",
                    buttons=[[Button.inline("◀️ Назад", b"menu")]]
                )
                return
            
            await event.edit(
                f"✅ Выбран режим: <b>Стильные пресеты</b>\n\n"
                f"Ваше имя: <b>{session.original_name}</b>\n"
                f"Создано вариантов: {len(session.variants)}\n\n"
                f"Примеры:\n"
                f"• {session.variants[0]}\n"
                f"• {session.variants[min(5, len(session.variants)-1)]}\n"
                f"• {session.variants[min(10, len(session.variants)-1)]}\n"
                f"• {session.variants[min(15, len(session.variants)-1)]}\n\n"
                f"Готовы начать?",
                buttons=[
                    [Button.inline("▶️ Запустить", b"start")],
                    [Button.inline("🔄 Показать еще", b"show_more_presets")],
                    [Button.inline("◀️ Назад", b"menu")],
                ],
                parse_mode='html'
            )
        
        elif data == "mode_custom":
            session.mode = 'custom'
            await event.edit(
                "📝 <b>Режим: Свои варианты</b>\n\n"
                "Отправьте список имен (каждое с новой строки).\n"
                "Максимум 64 символа на имя.\n\n"
                "Пример:\n"
                "<code>Мой Ник\n"
                "• Мой Ник •\n"
                "【Мой Ник】</code>",
                buttons=[[Button.inline("◀️ Назад", b"menu")]],
                parse_mode='html'
            )
        
        elif data == "mode_base":
            session.mode = 'base'
            await event.edit(
                "🔤 <b>Режим: Кастомная база</b>\n\n"
                "Отправьте любое имя, и я создам стильные вариации.\n\n"
                "Например:\n"
                "• Введите: <code>Alex</code>\n"
                "• Получите: »Alex«, ⚡ Alex ⚡, 『Alex』 и т.д.\n\n"
                "Или используйте свой текущий ник:",
                buttons=[
                    [Button.inline("✨ Использовать текущий", b"use_current")],
                    [Button.inline("◀️ Назад", b"menu")],
                ],
                parse_mode='html'
            )
        
        elif data == "show_more_presets":
            # Показать больше примеров пресетов
            if not session.variants:
                await event.answer("❌ Сначала сгенерируйте пресеты", alert=True)
                return
            
            # Случайные 10 вариантов
            examples = random.sample(session.variants, min(10, len(session.variants)))
            examples_text = "\n".join(f"• {v}" for v in examples)
            
            await event.edit(
                f"🎨 <b>Примеры пресетов</b>\n\n"
                f"Из {len(session.variants)} вариантов:\n\n"
                f"{examples_text}\n\n"
                f"При запуске будут использоваться все варианты случайным образом.",
                buttons=[
                    [Button.inline("▶️ Запустить", b"start")],
                    [Button.inline("🔄 Показать другие", b"show_more_presets")],
                    [Button.inline("◀️ Назад", b"menu")],
                ],
                parse_mode='html'
            )
            # Подключаемся к аккаунту пользователя
            await event.edit("⏳ Подключение к вашему аккаунту...", buttons=None)
            
            if not await self.connect_user(session):
                await event.edit(
                    "❌ Ошибка подключения\n\n"
                    "Отправьте /start для повторной попытки",
                    buttons=[[Button.inline("◀️ Назад", b"menu")]]
                )
                return
            
            # Генерируем варианты
            session.variants = NameVariantsGenerator.generate_from_base(session.original_name)
            
            await event.edit(
                f"✅ Варианты созданы!\n\n"
                f"Базовое имя: <b>{session.original_name}</b>\n"
                f"Вариантов: {len(session.variants)}\n\n"
                f"Примеры:\n"
                f"• {session.variants[0]}\n"
                f"• {session.variants[min(5, len(session.variants)-1)]}\n"
                f"• {session.variants[min(10, len(session.variants)-1)]}\n\n"
                f"Готовы начать?",
                buttons=[
                    [Button.inline("▶️ Запустить", b"start")],
                    [Button.inline("◀️ Назад", b"menu")],
                ],
                parse_mode='html'
            )
        
        elif data == "start":
            # Запуск смены ников
            if not session.variants:
                await event.answer("❌ Сначала выберите режим и настройте варианты", alert=True)
                return
            
            if session.running:
                await event.answer("⚠️ Уже запущено", alert=True)
                return
            
            # Подключение если еще не подключены
            if not session.client or not session.client.is_connected():
                await event.edit("⏳ Подключение...", buttons=None)
                if not await self.connect_user(session):
                    await event.edit("❌ Ошибка подключения", buttons=[[Button.inline("◀️ Назад", b"menu")]])
                    return
            
            # Запуск
            session.running = True
            session.task = asyncio.create_task(self.nick_change_loop(session, user_id))
            
            await event.edit(
                f"▶️ <b>ЗАПУЩЕНО</b>\n\n"
                f"Режим: {self._get_mode_name(session.mode)}\n"
                f"Вариантов: {len(session.variants)}\n"
                f"Оригинальный ник: <b>{session.original_name}</b>\n\n"
                f"{session.safety.get_stats()}\n\n"
                f"⚠️ При остановке ник вернется к оригинальному",
                buttons=[
                    [Button.inline("⏸ Остановить", b"stop")],
                    [Button.inline("📊 Статистика", b"stats")],
                ],
                parse_mode='html'
            )
        
        elif data == "stop":
            if not session.running:
                await event.answer("⚠️ Не запущено", alert=True)
                return
            
            await event.edit("⏳ Остановка...", buttons=None)
            
            # Остановка
            session.running = False
            if session.task:
                session.task.cancel()
                try:
                    await session.task
                except asyncio.CancelledError:
                    pass
            
            # Восстановление ника
            if session.client and session.original_name:
                try:
                    await session.client(UpdateProfileRequest(first_name=session.original_name))
                except:
                    pass
            
            await event.edit(
                f"⏸ <b>ОСТАНОВЛЕНО</b>\n\n"
                f"Ник восстановлен: <b>{session.original_name}</b>\n\n"
                f"{session.safety.get_stats()}",
                buttons=[[Button.inline("◀️ В меню", b"menu")]],
                parse_mode='html'
            )
        
        elif data == "stats":
            await event.answer(session.safety.get_stats(), alert=True)
        
        elif data == "menu":
            await self.handle_start(event)
        
        elif data == "help":
            help_text = (
                "📖 <b>ИНСТРУКЦИЯ</b>\n\n"
                "<b>Режимы работы:</b>\n\n"
                "🎨 <b>Стильные пресеты</b>\n"
                "Автоматическая генерация стильных вариаций вашего текущего ника. "
                "Добавляются символы, рамки, эмодзи и стилизация. "
                "Более 100 уникальных вариантов!\n\n"
                "📝 <b>Свои варианты</b>\n"
                "Введите свой список имен - каждое с новой строки. "
                "Бот будет случайно их чередовать.\n\n"
                "🔤 <b>Кастомная база</b>\n"
                "Введите любое имя (не обязательно ваше), и получите "
                "автоматически сгенерированные стильные вариации этого имени.\n\n"
                "<b>Безопасность:</b>\n"
                "├ Лимит 25 смен/час\n"
                "├ Лимит 400 смен/день\n"
                "├ Задержка 95-175 сек\n"
                "├ Авто FloodWait\n"
                "└ Восстановление при остановке\n\n"
                "<b>При остановке:</b>\n"
                "Ваш ник автоматически вернется к оригинальному!"
            )
            
            await event.edit(
                help_text,
                buttons=[[Button.inline("◀️ Назад", b"menu")]],
                parse_mode='html'
            )
    
    async def handle_message(self, event):
        """Обработка текстовых сообщений"""
        if event.is_private and not event.raw_text.startswith('/'):
            user_id = event.sender_id
            session = self.get_session(user_id)
            
            if session.mode == 'custom':
                # Парсинг пользовательских вариантов
                lines = [l.strip() for l in event.raw_text.split('\n') if l.strip()]
                variants = [l[:64] for l in lines if len(l) <= 64]
                
                if not variants:
                    await event.respond("❌ Не удалось распознать имена. Попробуйте снова.")
                    return
                
                session.custom_variants = variants
                session.variants = variants
                
                await event.respond(
                    f"✅ Принято вариантов: {len(variants)}\n\n"
                    f"Примеры:\n" + "\n".join(f"• {v}" for v in variants[:5]),
                    buttons=[
                        [Button.inline("▶️ Запустить", b"start")],
                        [Button.inline("◀️ Назад", b"menu")],
                    ]
                )
            
            elif session.mode == 'base':
                # Генерация на основе введенного имени
                base_name = event.raw_text.strip()[:30]
                
                if len(base_name) < 2:
                    await event.respond("❌ Слишком короткое имя")
                    return
                
                session.variants = NameVariantsGenerator.generate_from_base(base_name)
                
                await event.respond(
                    f"✅ Варианты созданы!\n\n"
                    f"Базовое имя: <b>{base_name}</b>\n"
                    f"Вариантов: {len(session.variants)}\n\n"
                    f"Примеры:\n"
                    f"• {session.variants[0]}\n"
                    f"• {session.variants[5]}\n"
                    f"• {session.variants[10]}",
                    buttons=[
                        [Button.inline("▶️ Запустить", b"start")],
                        [Button.inline("◀️ Назад", b"menu")],
                    ],
                    parse_mode='html'
                )
    
    async def connect_user(self, session: UserSession) -> bool:
        """Подключение к аккаунту"""
        try:
            session.client = TelegramClient(
                str(self.data_dir / f"session_{session.user_id}"),
                SERVICE_CONFIG['api_id'],
                SERVICE_CONFIG['api_hash']
            )
            
            await session.client.start()
            
            me = await session.client.get_me()
            session.original_name = me.first_name or "User"
            
            logger.info(f"Подключен пользователь {session.user_id}: @{me.username or 'N/A'}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения {session.user_id}: {e}")
            return False
    
    async def nick_change_loop(self, session: UserSession, user_id: int):
        
        try:
            while session.running:
                # Проверка безопасности
                can_change, message = session.safety.can_change_nick()
                
                if not can_change:
                    logger.info(f"User {user_id}: {message}")
                    await asyncio.sleep(60)
                    continue
                
                # Смена ника
                nick = random.choice(session.variants)
                
                try:
                    await session.client(UpdateProfileRequest(first_name=nick))
                    session.safety.register_change()
                    logger.info(f"User {user_id}: → {nick}")
                    
                except FloodWaitError as e:
                    session.safety.set_flood_wait(e.seconds)
                    logger.warning(f"User {user_id}: FloodWait {e.seconds}с")
                    await asyncio.sleep(e.seconds)
                    continue
                
                except Exception as e:
                    logger.error(f"User {user_id}: Ошибка смены: {e}")
                    await asyncio.sleep(60)
                    continue
                
                # Ожидание
                delay = session.safety.get_optimal_delay()
                await asyncio.sleep(delay)
        
        except asyncio.CancelledError:
            logger.info(f"User {user_id}: Цикл остановлен")
        except Exception as e:
            logger.error(f"User {user_id}: Критическая ошибка: {e}")
    
    def _get_mode_name(self, mode: str) -> str:
        """Название режима"""
        modes = {
            'preset': '🎨 Стильные пресеты',
            'custom': '📝 Свои варианты',
            'base': '🔤 Кастомная база'
        }
        return modes.get(mode, mode)


async def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("  GENTOOO AUTONICK SERVICE")
    print("="*60 + "\n")
    
    # Проверка конфигурации
    if not SERVICE_CONFIG['api_id'] or not SERVICE_CONFIG['api_hash'] or not SERVICE_CONFIG['bot_token']:
        print("⚠️  НАСТРОЙКА СЕРВИСА\n")
        print("1. Получите API ключи на https://my.telegram.org")
        print("2. Создайте бота через @BotFather")
        print("3. Укажите данные в SERVICE_CONFIG (строки 37-41)\n")
        print("   SERVICE_CONFIG = {")
        print("       'api_id': 12345678,")
        print("       'api_hash': 'your_api_hash',")
        print("       'bot_token': 'your:bot:token',")
        print("   }\n")
        return
    
    service = AutoNickService()
    
    try:
        await service.start_bot()
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка сервиса...")
        # Остановка всех активных сессий
        for session in service.sessions.values():
            if session.running:
                session.running = False
                if session.task:
                    session.task.cancel()
                if session.client and session.original_name:
                    try:
                        await session.client(UpdateProfileRequest(first_name=session.original_name))
                    except:
                        pass
        print("✅ Сервис остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nЗавершено.")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
