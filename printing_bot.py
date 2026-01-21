#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот-калькулятор для расчета стоимости широкоформатной печати
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Этапы разговора
MATERIAL, SIZE, QUANTITY, FINISHING = range(4)

# Прайс-лист (цены в рублях за кв.м)
MATERIALS = {
    '📄 Бумага (плакатная)': 150,
    '🖼 Фотобумага глянцевая': 350,
    '🎨 Холст': 500,
    '💎 Баннер (440 г/м²)': 400,
    '✨ Баннер (510 г/м²)': 450,
    '🪟 Пленка (самоклеющаяся)': 600,
    '🏢 Пленка (оракал)': 800,
}

# Дополнительные услуги
FINISHING_OPTIONS = {
    'Без отделки': 0,
    'Ламинирование': 200,
    'Люверсы (за шт)': 50,
    'Натяжка на подрамник': 500,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога - выбор материала"""
    user = update.effective_user
    
    keyboard = [[material] for material in MATERIALS.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я помогу рассчитать стоимость широкоформатной печати.\n\n"
        "Выберите материал для печати:",
        reply_markup=reply_markup
    )
    
    return MATERIAL


async def material_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение выбранного материала и запрос размеров"""
    material = update.message.text
    
    if material not in MATERIALS:
        await update.message.reply_text("Пожалуйста, выберите материал из предложенного списка.")
        return MATERIAL
    
    context.user_data['material'] = material
    context.user_data['price_per_sqm'] = MATERIALS[material]
    
    await update.message.reply_text(
        f"✅ Выбран материал: {material}\n"
        f"💰 Цена: {MATERIALS[material]} руб/м²\n\n"
        "Введите размеры (ширина x высота) в метрах.\n"
        "Например: 2.5x1.8 или 3x2",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return SIZE


async def size_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка размеров и запрос количества"""
    text = update.message.text.lower().replace(',', '.').replace(' ', '')
    
    try:
        # Парсинг размеров
        if 'x' in text or 'х' in text:  # латинская и русская "х"
            parts = text.replace('х', 'x').split('x')
            width = float(parts[0])
            height = float(parts[1])
        else:
            await update.message.reply_text(
                "❌ Неверный формат!\n"
                "Введите размеры в формате: ширина x высота\n"
                "Например: 2.5x1.8"
            )
            return SIZE
        
        if width <= 0 or height <= 0 or width > 10 or height > 10:
            await update.message.reply_text(
                "❌ Неверные размеры!\n"
                "Размеры должны быть положительными и не более 10 метров.\n"
                "Попробуйте еще раз:"
            )
            return SIZE
        
        area = width * height
        context.user_data['width'] = width
        context.user_data['height'] = height
        context.user_data['area'] = area
        
        await update.message.reply_text(
            f"✅ Размер: {width} x {height} м\n"
            f"📐 Площадь: {area:.2f} м²\n\n"
            "Введите количество экземпляров:"
        )
        
        return QUANTITY
        
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неверный формат!\n"
            "Введите размеры в формате: ширина x высота\n"
            "Например: 2.5x1.8"
        )
        return SIZE


async def quantity_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка количества и запрос дополнительных услуг"""
    try:
        quantity = int(update.message.text)
        
        if quantity <= 0 or quantity > 1000:
            await update.message.reply_text(
                "❌ Неверное количество!\n"
                "Введите число от 1 до 1000:"
            )
            return QUANTITY
        
        context.user_data['quantity'] = quantity
        
        keyboard = [[option] for option in FINISHING_OPTIONS.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ Количество: {quantity} шт.\n\n"
            "Выберите дополнительные услуги:",
            reply_markup=reply_markup
        )
        
        return FINISHING
        
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите целое число:"
        )
        return QUANTITY


async def calculate_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Расчет итоговой стоимости"""
    finishing = update.message.text
    
    if finishing not in FINISHING_OPTIONS:
        await update.message.reply_text("Пожалуйста, выберите опцию из списка.")
        return FINISHING
    
    # Получаем данные
    material = context.user_data['material']
    price_per_sqm = context.user_data['price_per_sqm']
    width = context.user_data['width']
    height = context.user_data['height']
    area = context.user_data['area']
    quantity = context.user_data['quantity']
    
    # Расчет стоимости
    printing_cost = price_per_sqm * area * quantity
    finishing_cost = 0
    
    if finishing == 'Люверсы (за шт)':
        # Предполагаем 4 люверса на изделие
        num_eyelets = 4 * quantity
        finishing_cost = FINISHING_OPTIONS[finishing] * num_eyelets
        finishing_details = f"{num_eyelets} шт x {FINISHING_OPTIONS[finishing]} руб"
    elif finishing != 'Без отделки':
        finishing_cost = FINISHING_OPTIONS[finishing] * quantity
        finishing_details = f"{quantity} шт x {FINISHING_OPTIONS[finishing]} руб"
    else:
        finishing_details = "0 руб"
    
    total_cost = printing_cost + finishing_cost
    
    # Формирование детального отчета
    report = (
        "═══════════════════════════════\n"
        "📊 РАСЧЕТ СТОИМОСТИ ЗАКАЗА\n"
        "═══════════════════════════════\n\n"
        f"📋 Материал: {material}\n"
        f"📏 Размер: {width} x {height} м ({area:.2f} м²)\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💰 Цена материала: {price_per_sqm} руб/м²\n\n"
        "───────────────────────────────\n"
        f"Стоимость печати:\n"
        f"{price_per_sqm} руб/м² × {area:.2f} м² × {quantity} шт = {printing_cost:.2f} руб\n\n"
    )
    
    if finishing_cost > 0:
        report += (
            f"Дополнительные услуги:\n"
            f"{finishing}: {finishing_details} = {finishing_cost:.2f} руб\n\n"
        )
    
    report += (
        "═══════════════════════════════\n"
        f"💳 ИТОГО: {total_cost:.2f} руб\n"
        "═══════════════════════════════\n\n"
        "Для нового расчета используйте /start\n"
        "Для отмены - /cancel"
    )
    
    await update.message.reply_text(report, reply_markup=ReplyKeyboardRemove())
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена расчета"""
    await update.message.reply_text(
        "❌ Расчет отменен.\n"
        "Для нового расчета используйте /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка по использованию бота"""
    help_text = (
        "🤖 Бот-калькулятор широкоформатной печати\n\n"
        "📋 Доступные команды:\n"
        "/start - Начать новый расчет\n"
        "/cancel - Отменить текущий расчет\n"
        "/help - Показать эту справку\n\n"
        "💡 Как пользоваться:\n"
        "1. Выберите материал для печати\n"
        "2. Введите размеры (например: 2.5x1.8)\n"
        "3. Укажите количество экземпляров\n"
        "4. Выберите дополнительные услуги\n"
        "5. Получите расчет стоимости\n\n"
        "📞 По вопросам обращайтесь к администратору"
    )
    await update.message.reply_text(help_text)


def main() -> None:
    """Запуск бота"""
    # Вставьте сюда ваш токен от BotFather
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MATERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, material_chosen)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, size_entered)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_entered)],
            FINISHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_total)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
