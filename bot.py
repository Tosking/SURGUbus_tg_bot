from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from difflib import SequenceMatcher
import threading
import os
import json
import requestInfo
import dbconnect
import zlib
import base64

load_dotenv()
token = os.getenv("TOKEN")
application = ApplicationBuilder().token(token).build()

AWAITING_BUS_NUMBER, AWAITING_BUS_STOP = range(2)
busTimers = []

def similarity_percentage(s1, s2):
    matcher = SequenceMatcher(None, s1, s2)
    return matcher.ratio() * 100

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if(query.data == "notify"):
        await query.message.reply_text('Отправьте номер автобуса. Например 45:')
        return AWAITING_BUS_NUMBER
    elif(query.data == "remove_notify"):
        remove_job_if_exists(str(update.effective_message.chat_id), context)
        await context.bot.send_message(chat_id=update.effective_chat.id, 
        text=f"Отслеживание отменено")
    elif(query.data == "add_favorite"):
        await add_favorite(query.message.text, context, update)
    elif(query.data == "start"):
        remove_job_if_exists(str(update.effective_message.chat_id), context)
        await startMenu(update, context)
    elif(query.data.split("_")[0] == "favorite"):
        await favorite(update, context, int(query.data.split("_")[1]))
    elif(query.data.split("_")[0] == "delfav"):
        await deleteList(update, context, int(query.data.split("_")[1]))
    elif(query.data.split("_")[0] == "df"):
        await deleteFavorite(context, update, query.data.split("_")[1])
    elif(query.data.startswith("s")):
        await startFavorite(query, context, update)
    elif(query.data.startswith("n")):
        await changeDir(query, context, update)
    elif(query.data.startswith("printstop")):
        await printStops(query, context, update)

async def deleteFavorite(context, update, id):
    dbconnect.delete_route(id)
    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Маршрут удален из избранного",
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data="start")]]))

async def deleteList(update, context, listNum):
    favList = dbconnect.get_routes_by_user(update.effective_message.chat_id)
    print(favList)
    start = listNum * 6
    end = start + 6
    keyboard = [[],[],[],[],[],[], [], [InlineKeyboardButton("Вернуться на главную страницу", callback_data=f"start")]]
    if listNum > 0:
        keyboard[3].append(InlineKeyboardButton("<", callback_data=f"delfav_{listNum - 1}"))
    if len(favList) < end:
        end = len(favList)
    else:
        keyboard[3].append(InlineKeyboardButton(">", callback_data=f"delfav_{listNum + 1}"))
    for i in range(start, end):
        print(i, end)
        keyboard[i % 6 // 1].append(InlineKeyboardButton(f"❌{favList[i][2]} - {favList[i][3]} - {favList[i][4]}", callback_data=f"df_{favList[i][0]}"))


    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Выберите какой избранный маршрут удалить",
    reply_markup=InlineKeyboardMarkup(keyboard))

async def printStops(query, context, update):
    number = query.data.split("_")[1]
    stops = []
    result = "Список возможных остановок:\n\n----------------\n\n"
    routesIds = requestInfo.getIdsOfRoute(number)
    for r in routesIds:
        forecastsId = requestInfo.getForecasts(str(r))
        for forecast in forecastsId:
            if not forecast['stname'] in stops:
                stops.append(forecast['stname'])
    for stop in stops:
        result += f"{stop}\n"
    result += "\n----------------\n\nВведите вашу остановку из списка:"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)

async def changeDir(query, context, update):
    notDir = query.data.split("_")[1]
    number = query.message.text.split(" ")[2][1::]
    stop = query.message.text.split("\"")[1]
    print(notDir, number, stop)
    route, routeId = await findClosestBus(number, stop, notDir)
    if route == None:
        await context.bot.send_message(chat_id=update.effective_chat.id, 
        text=f"Маршрут не найден")
        return
    remove_job_if_exists(str(update.effective_message.chat_id), context)
    application.job_queue.run_once(busTimer, 20, chat_id=update.effective_message.chat_id, name=str(update.effective_message.chat_id), data={'route': route, 'routeId' : routeId, 'lastTime' : route['arrt']})
    keyboard = [
        [InlineKeyboardButton("Добавить маршрут в избранное", callback_data="add_favorite")],
        [InlineKeyboardButton("Отменить слежение", callback_data="remove_notify")],
        [InlineKeyboardButton("Главное меню", callback_data="start")]
    ]

    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Ближайший автобус №{number} , направляющийся: {route['stdescr']}\nприбудет к остановке \"{route['stname']}\" через {route['arrt'] // 60} мин.",
    reply_markup=InlineKeyboardMarkup(keyboard))

async def startFavorite(query, context, update):
    favDb = dbconnect.get_routes_by_id(query.data.split("_")[1])[0]
    number, stname, direction = favDb[2], favDb[3], favDb[4]
    print(favDb)
    route, routeId = await findClosestBus(number, stname, direction=direction)
    if route == None:
        await context.bot.send_message(chat_id=update.effective_chat.id, 
        text=f"Маршрут не найден")
        return
    remove_job_if_exists(str(update.effective_message.chat_id), context)
    application.job_queue.run_once(busTimer, 20, chat_id=update.effective_message.chat_id, name=str(update.effective_message.chat_id), data={'route': route, 'routeId' : routeId, 'lastTime' : route['arrt']})
    keyboard = [
        [InlineKeyboardButton("В другую сторону", callback_data=f"n_{route['stdescr']}")],
        [InlineKeyboardButton("Отменить слежение", callback_data="remove_notify")],
        [InlineKeyboardButton("Главное меню", callback_data="start")]
    ]

    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Ближайший автобус №{number} , направляющийся: {route['stdescr']}\nприбудет к остановке \"{stname}\" через {route['arrt'] // 60} мин.",
    reply_markup=InlineKeyboardMarkup(keyboard))


async def favorite(update, context, listNum):
    favList = dbconnect.get_routes_by_user(update.effective_message.chat_id)
    print(favList)
    start = listNum * 6
    end = start + 6
    keyboard = [[],[],[],[],[],[], [],[InlineKeyboardButton("Удалить из избранного", callback_data="delfav_0")], 
    [InlineKeyboardButton("Вернуться на главную страницу", callback_data=f"start")]]
    if listNum > 0:
        keyboard[3].append(InlineKeyboardButton("<", callback_data=f"favorite_{listNum - 1}"))
    if len(favList) < end:
        end = len(favList)
    else:
        keyboard[3].append(InlineKeyboardButton(">", callback_data=f"favorite_{listNum + 1}"))
    for i in range(start, end):
        print(i, end)
        keyboard[i % 6 // 1].append(InlineKeyboardButton(f"{favList[i][2]} - {favList[i][3]} - {favList[i][4]}", callback_data=f"s_{favList[i][0]}"))


    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Выберите нужный маршрут",
    reply_markup=InlineKeyboardMarkup(keyboard))

    

async def add_favorite(message, context, update):
    favList = dbconnect.get_routes_by_user(update.effective_message.chat_id)
    if len(favList) > 100:
        await context.bot.send_message(chat_id=update.effective_message.chat_id, text=f"Достигнут лимит избранных маршрутов")
    number = message.split(" ")[2][1::]
    stop = message.split("\"")[1]
    direction = message.split(":")[1].split("\n")[0][1::]
    print(direction)
    if dbconnect.add_route(update.effective_message.chat_id, number, stop, direction):
        await context.bot.send_message(chat_id=update.effective_message.chat_id, text=f"Маршрут автобус №{number} и остановка {stop} были добавленны в избранное")
    else:
        await context.bot.send_message(chat_id=update.effective_message.chat_id, text=f"Данный маршрут уже находится в избранном")

async def get_bus_number(update, context):
    context.user_data['bus_number'] = update.message.text
    await update.message.reply_text('Теперь отправьте название остановки:', 
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Вывести список остановок", callback_data=f"printstop_{update.message.text}")]]))
    return AWAITING_BUS_STOP

# Обработка ввода названия остановки
async def get_bus_stop(update, context):
    context.user_data['bus_stop'] = update.message.text
    await notify(update, context)
    return ConversationHandler.END

async def cancel(update, context):
    update.message.reply_text('Действие отменено.')
    return ConversationHandler.END

async def findClosestBus(bus_number, bus_stop, notDir=None, direction=None):
    route = None
    routeId = None
    routesIds = requestInfo.getIdsOfRoute(bus_number)
    print(routesIds)
    for r in routesIds:
        forecastsId = requestInfo.getForecasts(str(r))
        for forecast in forecastsId:
            print(similarity_percentage(bus_stop.lower(), forecast["stname"].lower()), bus_stop, forecast["stname"], forecast['stdescr'])
            if similarity_percentage(bus_stop.lower(), forecast["stname"].lower()) >= 80 and notDir != forecast['stdescr'] and (direction == None or direction == forecast['stdescr']):
                if route == None or (forecast['arrt'] < route['arrt'] and forecast['arrt'] >= 60):
                    route = forecast
                    routeId = str(r)
    return route, routeId

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:

    current_jobs = context.job_queue.get_jobs_by_name(name)
    print(current_jobs, name)

    if not current_jobs:

        return False

    for job in current_jobs:

        job.schedule_removal()

    return True

async def busTimer(context):
    args = context.job.data
    job = context.job
    forecastsId = requestInfo.getForecasts(str(args['routeId']))
    forecast = [i for i in forecastsId if i['stname'] == args['route']['stname']]

    if len(forecast) == 0:
        await context.bot.send_message(chat_id=job.chat_id, text=f"Автобус приехал", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data="start")]]))
        remove_job_if_exists(str(job.chat_id), context)
        return
    else:
        forecast = forecast[0]
    minutes = forecast['arrt'] // 60
    lastMinutes = args['lastTime'] // 60
    if minutes > 5:
        if minutes != lastMinutes and minutes % 5 == 0:
            await context.bot.send_message(chat_id=job.chat_id, text=f"Автобус приедет через {minutes} мин")
    else:
        print(minutes, lastMinutes)
        if minutes != lastMinutes:
            await context.bot.send_message(chat_id=job.chat_id, text=f"Автобус приедет через {minutes} мин")
    for i in busTimers:
        if user == i['user']:
            i['timer'] = timer
    print(forecast)
    application.job_queue.run_once(busTimer, 20, chat_id=job.chat_id, name=str(job.chat_id), data={'route': args['route'], 'routeId' : args['routeId'], 'lastTime' :  forecast['arrt']})

async def notify(update, context):
    route, routeId = await findClosestBus(context.user_data['bus_number'], context.user_data['bus_stop'])
    if route == None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Автобус не обнаружен")
        return

    remove_job_if_exists(str(update.effective_message.chat_id), context)
    application.job_queue.run_once(busTimer, 20, chat_id=update.effective_message.chat_id, name=str(update.effective_message.chat_id), data={'route': route, 'routeId' : routeId, 'lastTime' : route['arrt']})
    keyboard = [
            [InlineKeyboardButton("В другую сторону", callback_data=f"n_{route['stdescr']}")],
            [
            InlineKeyboardButton("Добавить маршрут в избранное", callback_data="add_favorite"),
            InlineKeyboardButton("Отменить слежение", callback_data="remove_notify")
            ],
            [InlineKeyboardButton("Главное меню", callback_data="start")]
        ]


    await context.bot.send_message(chat_id=update.effective_chat.id, 
    text=f"Ближайший автобус №{context.user_data['bus_number']} , направляющийся: {route['stdescr']}\nприбудет к остановке \"{route['stname']}\" через {route['arrt'] // 60} мин.",
    reply_markup=InlineKeyboardMarkup(keyboard))



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Уведомить", callback_data="notify"),
            InlineKeyboardButton("Избранное", callback_data="favorite_0")
        ]
    ]
    dbconnect.add_user(update.message.from_user.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Бот для уведомления о приближающемся автобусе в г.Сургуте\nВыберите один из предложенных вариантов", reply_markup=InlineKeyboardMarkup(keyboard))

async def startMenu(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Уведомить", callback_data="notify"),
            InlineKeyboardButton("Избранное", callback_data="favorite_0")
        ]
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Бот для уведомления о приближающемся автобусе в г.Сургуте\nВыберите один из предложенных вариантов", 
    reply_markup=InlineKeyboardMarkup(keyboard))

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = ""
    routesIds = requestInfo.getIdsOfRoute(update.message.text)
    if(not routesIds):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Автобус не обнаружен")
        return
    print(routesIds)
    for i in routesIds:
        response += f'Автобус с айди: {i} ---------\n'
        forecasts = requestInfo.getForecasts(str(i))
        for k in forecasts:
            response += f'Время: {k["arrt"] // 60} мин. до остановки {k["stname"]} \n'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button)],
        states={
            AWAITING_BUS_NUMBER: [MessageHandler(filters.TEXT & (~filters.COMMAND), get_bus_number)],
            AWAITING_BUS_STOP: [MessageHandler(filters.TEXT & (~filters.COMMAND), get_bus_stop)],
        },
        fallbacks=[CallbackQueryHandler(button)]
    )


application.add_handler(conv_handler)
application.add_handler(CallbackQueryHandler(button))
application.add_handler(CommandHandler('start', start))
#application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))

def start():
    application.run_polling(allowed_updates=Update.ALL_TYPES)