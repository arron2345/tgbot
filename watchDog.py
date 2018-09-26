# -*- coding: utf-8 -*-
import sys
import logging
import json
import time
import random
import ConfigParser
from telegram import *
#KeyboardButton, ParseMode, ReplyKeyboardMarkup
from telegram.ext import *
# import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
#import schedule

reload(sys)  
sys.setdefaultencoding('utf8')


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

watchdogconfig = ConfigParser.ConfigParser()
watchdogconfig.read("watchdog.conf")
bottoken = watchdogconfig.get("bot","token")
botid=int(bottoken.split(":")[0])
puzzlesjson = watchdogconfig.get("puzzle","json")

WATCHDOGGROUP = int(watchdogconfig.get("group","id"))


file=open(puzzlesjson,"r")
PUZZLES = json.load(file)['puzzles']
file.close()

def callbackhandler(bot,update):
    message_id = update.callback_query.message.message_id
    activeuser = update.callback_query.from_user
    if not activeuser.id in ENTRANCE_PROGRESS:
        bot.sendMessage(activeuser.id,"请输入 /start 重新作答")
        return
    thedata = update.callback_query.data
    lasttext = PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question']
    if thedata == PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['answer']:
        #回答正确
        if ENTRANCE_PROGRESS[activeuser.id] == len(PUZZLES) - 1:
            #全部回答完毕
            unrestrict(WATCHDOGGROUP,activeuser.id)
            bot.sendMessage(activeuser.id,"您已全部作答正确，可以正常参与讨论")
            logger.warning("%s(%s)通过测试",newUser.full_name,newUser.id)
        else:
            bot.sendMessage(activeuser.id,"正确，下一题")
            ENTRANCE_PROGRESS[activeuser.id]+=1
            bot.sendMessage(activeuser.id,PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question'],reply_markup=buildpuzzlemarkup(PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['options']))
            
    else:
        #错误
            bot.sendMessage(activeuser.id,"答案不正确 请输入 /start 重新作答")
            del ENTRANCE_PROGRESS[activeuser.id]

    update.callback_query.edit_message_text( text = lasttext)
            
def buildpuzzlemarkup(options):
    keys = []
    random.shuffle(options)
    for each in options:
        keys.append([InlineKeyboardButton(each[1],callback_data=each[0])])
    return InlineKeyboardMarkup(keys)
    

ENTRANCE_PROGRESS={}

def botcommandhandler(bot,update):
    if "/join" in update.message.text:
        update.message.reply_text(bot.exportChatInviteLink(BNB48TEST))
        return
    #start in private mode
    if update.message.chat_id != update.message.from_user.id:
        return
    update.message.reply_text(PUZZLES[0]['question'],reply_markup=buildpuzzlemarkup(PUZZLES[0]['options']))
    ENTRANCE_PROGRESS[update.message.chat_id] = 0
        

def welcome(bot, update):
    if update.message.chat_id == WATCHDOGGROUP:
        for newUser in update.message.new_chat_members:
            logger.warning("%s(%s)加入%s",newUser.full_name,newUser.id,update.message.chat.title)
            restrict(update.message.chat_id,newUser.id,0.4)
            logger.warning("已禁言")
            try:
                bot.sendMessage(newUser.id,"请私聊[机器人](tg://user?id={})完成入群测试后后参与讨论".format(botid),parse_mode=ParseMode.MARKDOWN)
            except:
                logger.warning("向%s(%s)发送入群须知失败",newUser.full_name,newUser.id)
            

def ban(chatid,userid):
    updater.bot.kickChatMember(chatid,userid)

def kick(chatid,userid):
    updater.bot.kickChatMember(chatid,userid)
    updater.bot.unbanChatMember(chatid,userid)

def restrict(chatid,userid,minutes):
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=False,until_date=time.time()+int(float(minutes)*60))

def unrestrict(chatid,userid):
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=True,can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



updater = Updater(token=bottoken)

def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CallbackQueryHandler(callbackhandler))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))#'''处理新成员加入'''
    #dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, onleft))#'''处理成员离开'''

    dp.add_handler(CommandHandler(
        [
            "start",
            "join"
        ],
        botcommandhandler))# '''处理大群中的直接消息'''

    # log all errors
    dp.add_error_handler(error)



    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == '__main__':
    
    main()

