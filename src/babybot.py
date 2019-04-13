from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import sys
import os
import re
import sqlite3
from collections import Counter
from string import punctuation
from math import sqrt
from bs4 import BeautifulSoup
import urllib.request

# initialize the connection to the database
connection = sqlite3.connect('chatbot.sqlite')
cursor = connection.cursor()

# create the tables needed by the program
create_table_request_list = [
    'CREATE TABLE words(word TEXT UNIQUE)',
    'CREATE TABLE sentences(sentence TEXT UNIQUE, used INT NOT NULL DEFAULT 0)',
    'CREATE TABLE associations (word_id INT NOT NULL, sentence_id INT NOT NULL, weight REAL NOT NULL)',
]
for create_table_request in create_table_request_list:
    try:
        cursor.execute(create_table_request)
    except:
        pass


def get_id(entityName, text):
    """Retrieve an entity's unique ID from the database, given its associated text.
    If the row is not already present, it is inserted.
    The entity can either be a sentence or a word."""
    tableName = entityName + 's'
    columnName = entityName
    cursor.execute('SELECT rowid FROM ' + tableName + ' WHERE ' + columnName + ' = ?', (text,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute('INSERT INTO ' + tableName + ' (' + columnName + ') VALUES (?)', (text,))
        return cursor.lastrowid


def get_words(text):
    """Retrieve the words present in a given string of text.
    The return value is a list of tuples where the first member is a lowercase word,
    and the second member the number of time it is present in the text."""
    wordsRegexpString = '(?:\w+|[' + re.escape(punctuation) + ']+)'
    wordsRegexp = re.compile(wordsRegexpString)
    wordsList = wordsRegexp.findall(text.lower())
    return Counter(wordsList).items()


def printReply(replyStr):
    try:
        messageDiv = driver.find_element_by_id("main")
        pmessageBox = messageDiv.find_element_by_class_name("_3pkkz")
        messageBox = pmessageBox.find_element_by_class_name("selectable-text")
        messageBox.send_keys(replyStr)
        messageBox.send_keys(Keys.RETURN)
        print(messageBox.text)
    except Exception as e:
        print(str(e))

if os.name == "nt":
    driverPath = "driver/chromedriver_2.24.exe"
    dataPath = "Data"
else:
    driverPath = "driver/chromedriver"
    dataPath = "Data/ChatBot"


options = webdriver.ChromeOptions()
options.add_argument("--user-data-dir=" + dataPath)
driver = webdriver.Chrome(chrome_options=options, executable_path=driverPath)
driver.get('https://web.whatsapp.com')

input("Choose a chat on whatsapp and press enter : ")
chatHistory = []
replyQueue = []
firstRun = True

print("Starting...")

newMessages = []
chatHistory = []
chatHistory.append("Hello")


def storeAssociation(B,H):
    words = get_words(B)
    words_length = sum([n * len(word) for word, n in words])
    sentence_id = get_id('sentence', H)
    for word, n in words:
        word_id = get_id('word', word)
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO associations VALUES (?, ?, ?)', (word_id, sentence_id, weight))
    connection.commit()

def getReply(B,H):
    # retrieve the most likely answer from the database
    cursor.execute('CREATE TEMPORARY TABLE results(sentence_id INT, sentence TEXT, weight REAL)')
    words = get_words(H)
    words_length = sum([n * len(word) for word, n in words])
    for word, n in words:
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO results SELECT associations.sentence_id, sentences.sentence, ?*associations.weight/(4+sentences.used) FROM words INNER JOIN associations ON associations.word_id=words.rowid INNER JOIN sentences ON sentences.rowid=associations.sentence_id WHERE words.word=?',(weight, word,))
    # if matches were found, give the best one
    cursor.execute('SELECT sentence_id, sentence, SUM(weight) AS sum_weight FROM results GROUP BY sentence_id ORDER BY sum_weight DESC LIMIT 1')
    row = cursor.fetchone()
    cursor.execute('DROP TABLE results')
    # otherwise, just randomly pick one of the least used sentences
    if row is None:
        cursor.execute(
            'SELECT rowid, sentence FROM sentences WHERE used = (SELECT MIN(used) FROM sentences) ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
    # tell the database the sentence has been used once more, and prepare the sentence
    B = row[1]
    cursor.execute('UPDATE sentences SET used=used+1 WHERE rowid=?', (row[0],))
    return B

def about():
    return "BabyBot Developed By: Devang Chhajed and Mrinal Maheshwari"


def getSPITUpdates():
    spurl = "http://www.spit.ac.in/news-events/"
    page = urllib.request.urlopen(spurl)
    soup = BeautifulSoup(page, "html.parser")
    sidebar = soup.find_all('div', {"class": 'post-heading'})
    i=1
    reply = ""
    for item in sidebar:
        if i > 5:
            break
        a = item.find('a')
        title = a.text
        string = "*" + str(i) + "*. " + title
        reply+=string+"\n"
        i+=1

    return reply


def bot(userReply, B):
    H = userReply.strip()
    print("User: ", H)
    if H == '':
        print("continue")
        return

    if(H==".about"):
        return about()
    elif(H==".spupdates"):
        return getSPITUpdates()
    elif(H == "terminate"):
        return "5fa4035c75a44b890aa94cf0ff7f1b4a"
    else:
        storeAssociation(B,H)
        B = getReply(B,H)
        print('Bot: ' + B)
        return B


if __name__=='__main__':
    B = 'Hello!'
    while True:
        try:
            usersDiv = driver.find_element_by_id("side")
            messageDiv = driver.find_element_by_id("main")
            messageList = messageDiv.find_elements_by_class_name("message-in")

            message = messageList[-1]
            try:
                bubbleText = message.find_element_by_class_name("selectable-text").text
                if(chatHistory[-1]==bubbleText or bubbleText==B):
                    continue
                else:
                    chatHistory.append(bubbleText)
                    B = bot(bubbleText, B)
                    if(B == "5fa4035c75a44b890aa94cf0ff7f1b4a"):
                        printReply("Bye")
                        break
                    printReply(B)
            except Exception as e:
                print(str(e))
                pass

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)