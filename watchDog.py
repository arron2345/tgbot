#!/usr/bin/python
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
botname = watchdogconfig.get("bot","name")
groupid = int(watchdogconfig.get("group","id"))
groupname = watchdogconfig.get("group","name")
probation = int(watchdogconfig.get("group","probation"))

puzzlesjson = watchdogconfig.get("puzzle","json")

WATCHDOGGROUP = int(watchdogconfig.get("group","id"))


file=open(puzzlesjson,"r")
PUZZLES = json.load(file)['puzzles']
file.close()

lastpublicid = 0 #keep only one hint message
kickjobs = {}

def ban(chatid,userid):
    updater.bot.kickChatMember(chatid,userid)

def kick(chatid,userid):
    updater.bot.kickChatMember(chatid,userid)
    updater.bot.unbanChatMember(chatid,userid)

def watchdogkick(bot,job):
    kick(WATCHDOGGROUP,job.context.id)
    logger.warning("%s(%s)被踢出群",job.context.full_name,job.context.id)

def restrict(chatid,userid,minutes):
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=False,until_date=time.time()+int(float(minutes)*60))

def unrestrict(chatid,userid):
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=True,can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
def callbackhandler(bot,update):
    message_id = update.callback_query.message.message_id
    activeuser = update.callback_query.from_user
    if not activeuser.id in ENTRANCE_PROGRESS:
        bot.sendMessage(activeuser.id,"如回答错误，请输入 /start 重新作答！")
        return
    thedata = update.callback_query.data
    lasttext = PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question']
    if thedata == PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['answer']:
        #回答正确
        if ENTRANCE_PROGRESS[activeuser.id] == len(PUZZLES) - 1:
            #全部回答完毕
            global kickjobs
            if activeuser.id in kickjobs:
                kickjobs[activeuser.id].schedule_removal()
                del kickjobs[activeuser.id]
            unrestrict(WATCHDOGGROUP,activeuser.id)
            bot.sendMessage(activeuser.id,"您已全部作答正确，可以正常参与讨论")
            logger.warning("%s(%s)通过测试并解封",activeuser.full_name,activeuser.id)
        else:
            bot.sendMessage(activeuser.id,"正确，下一题")
            ENTRANCE_PROGRESS[activeuser.id]+=1
            bot.sendMessage(activeuser.id,PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question'],reply_markup=buildpuzzlemarkup(PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['options']))
            
    else:
        #错误
            bot.sendMessage(activeuser.id,"答案不正确，请输入 /start 重新作答！")
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
    if update.message.chat_id  == WATCHDOGGROUP:
        for newUser in update.message.new_chat_members:
            logger.warning("%s(%s)加入%s",newUser.full_name,newUser.id,update.message.chat.title)
            restrict(update.message.chat_id,newUser.id,0.4)
            logger.warning("已禁言")
            kickjobs[newUser.id] = jobqueue.run_once(watchdogkick,probation*60,context = newUser)
            logger.warning("已启动%s分钟踢出计时器",probation)

            global lastpublicid
            if lastpublicid != 0:
                bot.deleteMessage(WATCHDOGGROUP,lastpublicid)
            lastpublicid = update.message.reply_markdown("新用户请在{}分钟内私聊[机器人](tg://user?id={})完成入群测试".format(probation,botid))
            update.message.delete()

            try:
                bot.sendMessage(newUser.id,"请发送 /start 完成入群测试".format(botid),parse_mode=ParseMode.MARKDOWN)
            except:
                pass
                #logger.warning("向%s(%s)私聊发送入群须知失败",newUser.full_name,newUser.id)
            

    

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



updater = Updater(token=bottoken)
jobqueue = updater.job_queue

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
    logger.warning("机器人%s(%s)开始看守%s(%s)",watchdogconfig.get("bot","name"),watchdogconfig.get("bot","token"),watchdogconfig.get("group","name"),watchdogconfig.get("group","id"))
    main()
