
import os
import requests
import re
import string
import datetime
import time
from nltk.corpus import stopwords
from textblob import TextBlob
from bs4 import BeautifulSoup
#from nltk.tokenize import word_tokenize
from os import path
from twilio.rest import Client
from configparser import ConfigParser

""" Default Settings """


StockExchanges = ['Nasdaq','NYSE'] #Capitalization doesn't matter

KeyWords = ['positive results', 'end point', 'merge', 'definitive agreement', 'misses',
                  'all-stock deal', 'all-stock transaction', 'revenues beat',
                  'reported increased revenue', 'reports increased revenue', 'to acquire',
                  'revenues rise', 'tops q1', 'tops q2', 'tops q3', 'tops q4', 'development deal',
                  'skyrockets', 'signs deal', 'acquisition', 'positive results',
                  'acquires']
MinorKeyWords = ['announced today', 'better than']

MinorKWCount = 2

StartTimeSeek = 120 # Start at X minutes ago
Frequency = 60 # Run every X seconds
PauseTime = datetime.datetime.now()
SearchDepth = 2000

ProgramOn = True
Active = True
Weekdays = [
    dict(name="Monday", active = True, wake = '07:00', sleep = '20:00'),
    dict(name="Tuesday", active = True, wake = '07:00', sleep = '20:00'),
    dict(name="Wednesday", active = True, wake = '07:00', sleep = '20:00'),
    dict(name="Thursday", active = True, wake = '07:00', sleep = '20:00'),
    dict(name="Friday", active = True, wake = '07:00', sleep = '20:00'),
    dict(name="Saturday", active = False, wake = '07:00', sleep = '20:00'),
    dict(name="Sunday", active = False, wake = '07:00', sleep = '20:00')]
SkipDays = []
PauseTime = datetime.datetime.now()


""" Variables """

GlobeNewsWireMainURL = 'http://www.globenewswire.com'
StreetInsiderMainURL = 'https://www.streetinsider.com/Press+Releases'
LowPolarityValue = 0.01
MedPolarityValue = 0.3
HighPolarityValue = 0.6

#Devins info
account_sid = 'ENTER ACCOUNT SID HERE'
auth_token = 'ENTER AUTH TOKEN HERE'
TwilioNumber = 'ENTER TWILIO NUMBER HERE'
PhoneNumber = 'ENTER PHONE NUMBER HERE'

script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in


CommandsRel = "/Stock Input/Commands.txt"
MessagesRel = "/Stock Input/Messages.txt"

CommandsLoc = script_dir+CommandsRel
MessagesLoc = script_dir+MessagesRel

CommandsLoc = CommandsLoc.replace("/","//")
MessagesLoc = MessagesLoc.replace("/","//")

ConfigOpen = False

global client

config = ConfigParser()



""" Begin code - don't change beyond here """

def main():
    global ProgramOn
    global client
    global Frequency
    FirstSearch = True
    
    print("a")
    print(MessagesLoc)
    f = open(MessagesLoc,"r+")
    print("b")
    f.close()
    
    try:
        client = Client(account_sid, auth_token)
    except:
        print("Error with authentication. Check and make sure the SID and Token match those in Twilio")
    
    while ProgramOn:
        LoadSettings()
        Search(FirstSearch)
        if FirstSearch == True:
            FirstSearch = False
        SendTextMessage()
        print("Will run again in {} seconds...".format(Frequency))
        time.sleep(Frequency)
        ReadResponse()


""" Functions """

def Search(FirstSearch):
    global StartTimeSeek
    global Frequency
    
    StartTime = datetime.datetime.now()
    if FirstSearch:
        StopTime = GetBeginningTime(int(StartTimeSeek), True)
    else:
        StopTime = GetBeginningTime(Frequency, False)
    
    #StreetInsiderWebsite(StopTime)
    GlobeNewsWireWebsite(StopTime)
    
    EndTime = datetime.datetime.now()
    print("Search completed in {} seconds".format(round((EndTime-StartTime).total_seconds(),1)))
    

def ReadResponse():
    global ProgramOn
    global Active
    global MessagesLoc
    global CommandsLoc
    global Weekdays
    global SkipDays
    global KeyWords
    global MinorKeyWords
    global PauseTime
    f = None
    try:
        if path.exists(CommandsLoc):
            f = open(CommandsLoc, "r")
            lines = f.readlines()
            for line in lines:
                if line[0] == "\n":
                    continue
                if line[0] == "#":
                    break
                Command = line.lower().replace('\n', '')
                Words = Command.split()
                if Command == "exit":
                    ProgramOn = False
                    return
                elif Command == "turn off":
                    ChangeConfig('main', 'active', 'False')
                    SendText("Program has been turned off. Command 'TURN ON' will undo this")
                    
                elif Command == "turn on":
                    ChangeConfig('main', 'active', 'True')
                    SendText("Program has been turned back on")
                    
                elif Command == "clear messages":
                    open(MessagesLoc, 'w').close()
                    SendText("Messages cleared")
                    
                elif Words[0] == "search" and Words[1] == "first":
                    try:
                        n = int(Words[2])
                        ChangeConfig('main', 'searchdepth', n)
                        SendText("Program will now search through the first {} characters for keywords.".format(n))
                    except:
                        SendText("Invalid input for 'SEARCH FIRST #'")
                                    
                elif Words[0] == "frequency":
                    try:
                        n = int(Words[1])
                        if Words[2] == "minute" or Words[2] == "minutes":
                            ChangeConfig('main', 'frequency', n*60)
                        elif Words[2] == "second" or Words[2] == "seconds":
                            ChangeConfig('main', 'frequency', n)
                        else:
                            raise
                    except:
                        SendText("Invalid input for 'FREQUENCY # MINUTES/SECONDS'")
                                    
                elif Words[0] == "turn" and Words[1] == "off" and len(Words) == 4:
                    if isDigit(Words[2]):
                        if Words[3] == "minutes" or Words[3] == "minute":
                            PauseTime = datetime.datetime.now() + datetime.timedelta(minutes=int(Words[2]))
                            SendText("Program paused for {} minutes".format(Words[2]))
                        elif Words[3] == "hours" or Words[3] == "hour":
                            PauseTime = datetime.datetime.now() + datetime.timedelta(seconds=int(Words[2]))
                            SendText("Program paused for {} hours".format(Words[2]))
                        else:
                            SendText("Invalid input for 'TURN OFF # MINUTES/HOURS'")
                    else:
                        SendText("Invalid input for 'TURN OFF # MINUTES/HOURS'")
                elif Command == "list keywords":
                    SendText("Major keywords: "+", ".join(KeyWords))
                    SendText("Minor keywords: "+", ".join(MinorKeyWords))
                    
                elif Command == "list days":
                    m = ""
                    for d in Weekdays:
                        if d["active"]:
                            a = "Active"
                        else:
                            a = "Inactive"
                        m += "{} ({})- Wakes at {}, sleeps at {}. ".format(d["name"], a, d["wake"], d["sleep"])
                    SendText(m)
                    
                elif Command == "list days off":
                    SendText("Days off: "+", ".join(SkipDays))
                
                elif Command == "what up":
                    now = datetime.datetime.now()
                    h = time.strftime('%H')
                    m = time.strftime('%M')
                    day = now.weekday()
                    s = Weekdays[day]['sleep'].split(":")
                    w = Weekdays[day]["wake"].split(":")
                    if Active == False:
                        SendText("Program is set to inactive. Put in the command TURN ON to change this")
                    elif Weekdays[day]["active"] == False:
                        SendText("Program is off on {}s. Put in the command TURN ON {}".format(Weekdays[day]["name"], Weekdays[day]["name"].upper()))
                    elif int(h) > int(s[0]) or (int(h) == int(s[0]) and int(m) > int(s[1])):
                        SendText("Program is asleep for the day. Put in the command {} SLEEP HH:MM to change".format(Weekdays[day]["name"].upper()))
                    elif int(h) < int(w[0]) or (int(h) == int(w[0]) and int(m) < int(w[1])):
                        SendText("Program hasn't woken up yet. Put in the command {} WAKE HH:MM to change".format(Weekdays[day]["name"].upper()))
                    elif "{}:{}".format(now.month, now.day) in SkipDays:
                        SendText("Today is currently being skipped. Put in the command REMOVE DAY MM/DD to change")
                    elif PauseTime > now:
                        SendText("Program is currently paused. To remove this, put in the command TURN OFF 1 MINUTE")
                    
                    else:
                        SendText("Program is currently running")
                        
                    
                elif Words[0] == "add" and Words[1] == "keyword":
                    if Command.count('"') != 2:
                        SendText("Invalid input for 'ADD KEYWORD "+'"word or phrase"'+"' (must have quotes)")
                    k = Command[Command.find('"'):].replace('"','')
                    f = open('config.ini')
                    count = 0
                    section = False
                    for line in f:
                        if "keywords" in line:
                            section = True
                            continue
                        if section == False:
                            continue
                        if line == '\n':
                            break
                        count += 1
                    f.close()
                    ChangeConfig('keywords',str(count+1),k)
                    if k in MinorKeyWords:
                        DeleteConfig('minorkeywords',k)
                        SendText('Keyword "{}" changed from minor keyword to normal'.format(k))
                    else:
                        SendText('Keyword "{}" added to list of keywords'.format(k))
                        
                elif Words[0] == "add" and Words[1] == "minor" and Words[2] == "keyword":
                    if Command.count('"') != 2:
                        SendText("Invalid input for 'ADD MINOR KEYWORD "+'"word or phrase"'+"' (must have quotes)")
                    k = Command[Command.find('"'):].replace('"','')
                    f = open('config.ini')
                    count = 0
                    section = False
                    for line in f:
                        if "minorkeywords" in line:
                            section = True
                            continue
                        if section == False:
                            continue
                        if line == '\n':
                            break
                        count += 1
                    f.close()
                    ChangeConfig('minorkeywords',str(count+1),k)
                    if k in KeyWords:
                        DeleteConfig('keywords',k)
                        SendText('Keyword "{}" changed from normal keyword to minor'.format(k))
                    else:
                        SendText('Keyword "{}" added to list of minor keywords'.format(k))
                        
                elif Words[0] == "remove" and Words[1] == "keyword":
                    if Command.count('"') != 2:
                        SendText("Invalid input for 'REMOVE KEYWORD "+'"word or phrase"'+"' (must have quotes)")
                    k = Command[Command.find('"'):].replace('"','')
                    if k in KeyWords:
                        DeleteConfig('keywords',k)
                        SendText('Keyword "{}" removed from key words'.format(k))
                    elif k in MinorKeyWords:
                        DeleteConfig('minorkeywords',k)
                        SendText('Keyword "{}" removed from minor key words'.format(k))
                    else:
                        SendText('Keyword "{}" was not in list'.format(k))
                        
                elif Words[0] == "add" and Words[1] == "day" and Words[2] == "off":
                    if Words[3].count('/') == 1:
                        d = Words[3].split('/')
                        if len(d) == 2 and isDigit(d[0]) and isDigit(d[1]) and int(d[0]) in range(1,13) and int(d[1]) in range(1,32):
                            ChangeConfig('skipdays',int(len(SkipDays)+1),Words[3])
                        else:
                            SendText("Invalid input for 'ADD DAY OFF MM/DD'")
                    else:
                        SendText("Invalid input for 'ADD DAY OFF MM/DD'")
                        
                elif Words[0] == "remove" and Words[1] == "day" and Words[2] == "off":
                    if Words[3].count('/') == 1:
                        d = Words[3].split('/')
                        if len(d) == 2 and isDigit(d[0]) and isDigit(d[1]) and int(d[0]) in range(1,13) and int(d[1]) in range(1,32):
                            DeleteConfig('skipdays', Words[3])
                            SendText(Words[3]+' removed from days to skip')
                        else:
                            SendText("Invalid input for 'REMOVE DAY OFF MM/DD'")
                    else:
                        SendText("Invalid input for 'REMOVE DAY OFF MM/DD'")
                elif Command == "turn off today":
                    f = open('config.ini')
                    count = 0
                    section = False
                    for line in f:
                        if "skipdays" in line:
                            section = True
                            continue
                        if section == False:
                            continue
                        if line == '\n':
                            break
                        count += 1
                    f.close()
                    ChangeConfig('skipdays',str(count+1),"{}/{}".format(datetime.datetime.now().month, datetime.datetime.now().day))
                    SendText("Program will be turned off for today. Remove this day from the skipped days to reverse this.")
                    
                elif Command == "turn off tomorrow":
                    f = open('config.ini')
                    count = 0
                    section = False
                    for line in f:
                        if "skipdays" in line:
                            section = True
                            continue
                        if section == False:
                            continue
                        if line == '\n':
                            break
                        count += 1
                    f.close()
                    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
                    ChangeConfig('skipdays',str(count+1),"{}/{}".format(tomorrow.month, tomorrow.day))
                    SendText("Program will be turned off tomorrow. Remove tomorrows date from the skipped days to reverse this.")
                    
                elif Words[0] == "monday" or Words[1] == "mondays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','mondayactive',False)
                        SendText("Mondays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','mondayactive',True)
                        SendText("Mondays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','mondaywake',Words[2])
                                SendText("Monday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','mondaysleep',Words[2])
                                SendText("Monday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "tuesday" or Words[1] == "tuesdays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','tuesdayactive',False)
                        SendText("Tuesdays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','tuesdayactive',True)
                        SendText("Tuesdays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','tuesdaywake',Words[2])
                                SendText("Tuesday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','tuesdaysleep',Words[2])
                                SendText("Tuesday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "wednesday" or Words[1] == "wednesdays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','wednesdayactive',False)
                        SendText("Wednesdays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','wednesdayactive',True)
                        SendText("Wednesdays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','wednesdaywake',Words[2])
                                SendText("Wednesday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','wednesdaysleep',Words[2])
                                SendText("Wednesday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "thursday" or Words[1] == "thursdays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','thursdayactive',False)
                        SendText("Thursdays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','thursdayactive',True)
                        SendText("Thursdays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','thursdaywake',Words[2])
                                SendText("Thursday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','thursdaysleep',Words[2])
                                SendText("Thursday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "friday" or Words[1] == "fridays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','fridayactive',False)
                        SendText("Fridays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','fridayactive',True)
                        SendText("Fridays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','fridaywake',Words[2])
                                SendText("Friday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','fridaysleep',Words[2])
                                SendText("Friday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "saturday" or Words[1] == "saturdays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','saturdayactive',False)
                        SendText("Saturdays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','saturdayactive',True)
                        SendText("Saturdays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','saturdaywake',Words[2])
                                SendText("Saturday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','saturdaysleep',Words[2])
                                SendText("Saturday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                elif Words[0] == "sunday" or Words[1] == "sundays":
                    if Words[1] == "off":
                        ChangeConfig('weekdays','sundayactive',False)
                        SendText("Sundays have been turned off")
                    elif Words[1] == "on":
                        ChangeConfig('weekdays','sundayactive',True)
                        SendText("Sundays have been turned back on")
                    elif Words[2].count(':') == 1:
                        t = Words[2].split(':')
                        if isDigit(t[0]) and int(t[0]) in range(1,25) and isDigit(t[1]) and int(t[1]) in range(0,61):
                            if Words[1] == "wake":
                                ChangeConfig('weekdays','sundaywake',Words[2])
                                SendText("Sunday wake time has been changed to "+Words[2])
                            elif Words[1] == "sleep":
                                ChangeConfig('weekdays','sundaysleep',Words[2])
                                SendText("Sunday sleep time has been changed to "+Words[2])
                            else:
                                SendText("Invalid input for command")
                        else:
                            SendText("Invalid input for command")
                    else:
                        SendText("Invalid input for command")
                else:
                    print("Unknown command")
            f.close()
            f = open(CommandsLoc, "w")
            Comment = False
            for line in lines:
                if line[0] == '#' or Comment == True:
                    Comment = True
                else:
                    continue
                f.write(line)
                    
        else:
            print("Couldn't find Stock Input.txt in folder")
        
    except:
        print("Error when loading Stock Input file")
        
def ChangeConfig(section, key, value):
    # set new value
    config = ConfigParser()
    config.read("config.ini")
    config.set(section, str(key), str(value))
    
    # save the file
    with open("config.ini", "w") as f:
        config.write(f)
        
def isDigit(string):
    try:
        a = int(string)
        return True
    except:
        return False
        
        
def DeleteConfig(section, value):
    fname = 'config.ini'
    f = open(fname)
    output = []
    Section = False
    for line in f:
        if section in line:
            Section = True
        if not value in line or Section == False:
            output.append(line)
    f.close()
    f = open(fname, 'w')
    f.writelines(output)
    f.close()

def IsValidTicker(TickerList):
    Tickers = TickerList.split(", ")
    ValidTickers = []
    for t in Tickers:
        if not t:
            continue
        t = t.split(":")
        if any(t[0].lower() == SE.lower() for SE in StockExchanges): 
            ValidTickers.append(t[1])
    if ValidTickers != [''] and ValidTickers != []:
        return ValidTickers
    else:
        return ''


def  CleanText(ImportText):
    #Remove anything with a number
    NoNumbers = ' '.join(s for s in ImportText.split() if not any(c.isdigit() for c in s))
    
    #Remove links
    HTTP = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    RemoveLinks = HTTP.sub('', NoNumbers)
    
    #Remove emails
    Email = re.compile('(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))@(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    RemoveEmails = Email.sub('', RemoveLinks)
    
    #Remove punctuation
    NoPunctuation = RemoveEmails.translate(str.maketrans('', '', string.punctuation))
    
    #Remove stopwords (a, and, in, etc...)
    #text_tokens = word_tokenize(NoPunctuation)
    FilteredWords = [word for word in NoPunctuation if not word in stopwords.words()]
    
    #Combine together to be used as text block
    FinalText = ""
    for word in FilteredWords:
        FinalText += word
        FinalText += " "
    return FinalText


def FindSentiment(InputBlob, ngram):
    VeryBad = 0
    Bad = 0
    SlightlyBad = 0
    NonZero = 0
    SlightlyGood = 0
    Good = 0
    VeryGood = 0
    
    for l in InputBlob.ngrams(n=ngram):
        l = str(l)
        l = TextBlob(l)
        if l.polarity > HighPolarityValue:
            VeryGood += 5
        elif l.polarity <= HighPolarityValue and l.polarity > MedPolarityValue:
            Good += 3
        elif l.polarity <= MedPolarityValue and l.polarity > LowPolarityValue:
            SlightlyGood += 1
        elif l.polarity < -LowPolarityValue and l.polarity >= -MedPolarityValue:
            SlightlyBad += 1
        elif l.polarity < -MedPolarityValue and l.polarity >= -HighPolarityValue:
            Bad += 1
        elif l.polarity < -HighPolarityValue:
            VeryBad += 1
        if l.polarity > LowPolarityValue or l.polarity < -LowPolarityValue:
            NonZero += 1
    #print("{} : {}".format("VeryBad", VeryBad))
    #print("{} : {}".format("Bad", Bad))
    #print("{} : {}".format("SlightlyBad", SlightlyBad))
    #print("{} : {}".format("NonZero", NonZero))
    #print("{} : {}".format("SlightlyGood", SlightlyGood))
    #print("{} : {}".format("Good", Good))
    #print("{} : {}".format("VeryGood", VeryGood))
    if NonZero != 0:
        if (VeryGood+Good+SlightlyGood)/NonZero > .5:
            print("Good news")
        else:
            print("Bad news")
    else:
        print("Neutral news")
    

def GlobeNewsWirePage(PageURL, StopTime):
    global MinorKWCount
    page = requests.get(PageURL)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    # Open each of the 10 news pages on the front page
    for a in soup.find_all('a', href=lambda href: href and "news-release" in href):
        # Get the URL
        NewsPageURL = GlobeNewsWireMainURL+a['href']
        
        # Retrieve the page
        subpage = requests.get(NewsPageURL)
        subsoup = BeautifulSoup(subpage.content, 'html.parser')
        
        # Filter out unusable/missing tickers
        try:
            LongTicker = subsoup.find("meta", {"name":"ticker"})['content']
        except:
            continue
        Ticker = IsValidTicker(LongTicker)
        if Ticker == "":
            continue
        
        #Company Name
        CompanyNameTag = subsoup.find("span", itemprop="name")
        CompanyName = CompanyNameTag.text
            
        #Get the date the article came out - stops at most recent article
        PublishedDateTag = subsoup.find("time")
        PublishedDate = PublishedDateTag.text
        DT = datetime.datetime.strptime(PublishedDate, '%B %d, %Y %H:%M ET')
        
        # If we have looked at articles at this time we don't need to continue
        if DT < StopTime:
            print("Reached end of time frame to search.")
            return True
        
        #Subtract everything but paragraph section of page
        BodyTextWithTags = subsoup.find(class_='article-body')
        
        #Subtract tags and set everything to lower case
        BodyText = BodyTextWithTags.text.lower()
        
        #Delete intro date stuff
        BodyText = BodyText[BodyText.find(' -- '):]
        
        #Search for any keywords
        keywordcount = KeyWordsFilter(BodyText)
        if keywordcount == None:
            continue
        totalcount = 0
        for i in keywordcount:
            totalcount += i[1]
            
        # Check minor key words
        if totalcount == 0:
            #Search for any keywords
            keywordcount = MinorKeyWordsFilter(BodyText)
            if keywordcount == None:
                continue
            totalcount = 0
            for i in keywordcount:
                totalcount += i[1]
            if totalcount < MinorKWCount:
                continue
        
        FinalText = CleanText(BodyText)
        
        #print(FinalText)
        blob = TextBlob(FinalText)
        
        #Output
        if blob.polarity > 0.3:
            sent = "Very Positive"
        elif blob.polarity > 0.1:
            sent = "Positive"
        elif blob.polarity < -0.3:
            sent = "Very Negative"
        elif blob.polarity < -0.1:
            sent = "Negative"
        else:
            sent = "Neutral"
        m = "{} ({}) - {}. {} keyword(s): ".format(CompanyName, ArrayToString(Ticker), sent, totalcount )
        if len(keywordcount) > 0 and int(keywordcount[0][1]) > 0:
            m += "'{}' ({})".format(keywordcount[0][0], keywordcount[0][1])
        if len(keywordcount) > 1 and int(keywordcount[1][1]) > 0:
            m += ", '{}' ({})".format(keywordcount[1][0], keywordcount[1][1])
        if len(keywordcount) > 2 and int(keywordcount[2][1]) > 0:
            m += ", '{}' ({}) ".format(keywordcount[2][0], keywordcount[2][1])
        m += " -- {}".format(NewsPageURL)
        SaveMessage(m)
        #SaveMessage(GetGoogleTrendsLink(Ticker))
        
    return False
            
            
def GlobeNewsWireWebsite(StopTime):
    for i in range(1,101):
        print()
        print("Returning GlobeNewsWire page {}...".format(i))
        Page = GlobeNewsWireMainURL+'/Index?page='
        Page += str(i)
        Page += '#pagerPos'
        
        if GlobeNewsWirePage(Page, StopTime) == True:
            #If the most recently searched article is on this page
            break
        
"""def StreetInsiderPage(PageURL, StopTime):
    page = requests.get(PageURL)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    print(soup.prettify())
    return
    
def StreetInsiderWebsite(StopTime):
    for i in range(1,2):
        print()
        print("Returning StreetInsider page {}...".format(i))
        Page = StreetInsiderMainURL+'/?offset='
        Page += str(5+50*i)
        
        if StreetInsiderPage(Page, StopTime) == True:
            #If the most recently searched article is on this page
            break"""

        
def KeyWordsFilter(Text):
    global KeyWords
    c = []
    found = False
    for word in KeyWords:
        c.append([word, Text[0:SearchDepth].count(word)])
        if found == False and Text[0:SearchDepth].count(word) > 0:
            found = True
    cs = sorted(c, key=lambda x: x[1], reverse=True)
    if found == False:
        return None
    else:
        return cs
    
def MinorKeyWordsFilter(Text):
    global MinorKeyWords
    c = []
    found = False
    for word in MinorKeyWords:
        c.append([word, Text[0:SearchDepth].count(word)])
        if found == False and Text[0:SearchDepth].count(word) > 0:
            found = True
    cs = sorted(c, key=lambda x: x[1], reverse=True)
    if found == False:
        return None
    else:
        return cs
        

def SaveMessage(Text):
    global MessagesLoc
    try:
        f = open(MessagesLoc, "a+")
        f.write("{}\n".format(Text))
        f.close()
    except:
        print("Error has occurred when saving a message")
        
        
        
def SendTextMessage():
    global MessagesLoc
    global Weekdays
    global PauseTime
    global TwilioNumber
    global PhoneNumber
    global client
    global Active
    now = datetime.datetime.now()
    h = time.strftime('%H')
    m = time.strftime('%M')
    weekday = datetime.datetime.today().weekday()
    if Active == False or Active == "False":
        return
    if "{}:{}".format(now.month, now.day) in SkipDays:
        return
    if PauseTime > now:
        return
    if not Weekdays[weekday]["active"]:
        return
    s = Weekdays[weekday]['sleep'].split(":")
    if int(h) > int(s[0]) or (int(h) == int(s[0]) and int(m) > int(s[1])):
        return
    w = Weekdays[weekday]["wake"].split(":")
    if int(h) < int(w[0]) or (int(h) == int(w[0]) and int(m) < int(w[1])):
        return
    filename = MessagesLoc
    try:
        print("a")
        f = open(filename, "r+")
        print("b")
        text = f.readlines()
        f.truncate(0)
        f.close()
        for line in text:
            if line == "\n":
                continue
            client.messages.create( 
                              from_=TwilioNumber, 
                              body =line, 
                              to = PhoneNumber
                          )
            print("TEXT: {}".format(line))
    except:
        print("Error has occurred when sending a message")
        
def SendText(Text):
    client.messages.create( 
                              from_=TwilioNumber, 
                              body =Text, 
                              to = PhoneNumber
                          )
        
    
def GetGoogleTrendsLink(Ticker):
    return "https://trends.google.com/trends/explore?q={}&hl=en-US".format(Ticker)


def ArrayToString(Array):
    return ", ".join(Array) #Collection


def GetBeginningTime(Time, boolUsesMinutes):
    if boolUsesMinutes:
        DeltaTime = datetime.timedelta(minutes=Time)
    else:
        DeltaTime = datetime.timedelta(seconds=Time)
    CurrentTime = datetime.datetime.now()
    return(CurrentTime - DeltaTime)
    

def LoadSettings():
    filename = "config.ini"
    global config
    global StockExchanges
    global KeyWords
    global MinorKeyWords
    global StartTimeSeek
    global Frequency
    global Weekdays
    global SkipDays
    global Active
    global SearchDepth
    global ConfigOpen
    global ProgramOn
    fname = 'config.ini'
    if path.exists(fname):
        with open(fname) as f:
            mylist = f.read().splitlines() 
        mainList = []
        stockexchangesList = []
        weekdaysList = []
        keywordsList = []
        minorkeywordsList = []
        listcount = 0
        for line in mylist:
            if line == '':
                continue
            if '[main]' in line:
                continue
            if '[stockexchanges]' in line:
                listcount = 1
                continue
            if '[weekdays]' in line:
                listcount = 2
                continue
            if '[keywords]' in line:
                listcount = 3
                continue
            if '[minorkeywords]' in line:
                listcount = 4
                continue
            if listcount == 0:
                mainList.append(line)
            elif listcount == 1:
                stockexchangesList.append(line)
            elif listcount == 2:
                weekdaysList.append(line)
            elif listcount == 3:
                keywordsList.append(line)
            elif listcount == 4:
                minorkeywordsList.append(line)
                
        for entry in mainList:
            e = entry.split(" = ")
            if 'active' in e[0]:
                Active = e[1]
            elif 'starttimeseek' in e[0]:
                StartTimeSeek = int(e[1])
            elif 'frequency' in e[0]:
                Frequency = int(e[1])
            elif 'searchdepth' in e[0]:
                SearchDepth = int(e[1])
            
        for entry in weekdaysList:
            e = entry.split(" = ")
            if 'mondayactive' in e[0]:
                Weekdays[0]['active'] = e[1]
            elif 'tuesdayactive' in e[0]:
                Weekdays[1]['active'] = e[1]
            elif 'wednesdayactive' in e[0]:
                Weekdays[2]['active'] = e[1]
            elif 'wednesdayactive' in e[0]:
                Weekdays[3]['active'] = e[1]
            elif 'fridayactive' in e[0]:
                Weekdays[4]['active'] = e[1]
            elif 'saturdayactive' in e[0]:
                Weekdays[5]['active'] = e[1]
            elif 'sundayactive' in e[0]:
                Weekdays[6]['active'] = e[1]
            elif 'mondaywake' in e[0]:
                Weekdays[0]['wake'] = e[1]
            elif 'tuesdaywake' in e[0]:
                Weekdays[1]['wake'] = e[1]
            elif 'wednesdaywake' in e[0]:
                Weekdays[2]['wake'] = e[1]
            elif 'wednesdaywake' in e[0]:
                Weekdays[3]['wake'] = e[1]
            elif 'fridaywake' in e[0]:
                Weekdays[4]['wake'] = e[1]
            elif 'saturdaywake' in e[0]:
                Weekdays[5]['wake'] = e[1]
            elif 'sundaywake' in e[0]:
                Weekdays[6]['wake'] = e[1]
            elif 'mondaysleep' in e[0]:
                Weekdays[0]['sleep'] = e[1]
            elif 'tuesdaysleep' in e[0]:
                Weekdays[1]['sleep'] = e[1]
            elif 'wednesdaysleep' in e[0]:
                Weekdays[2]['sleep'] = e[1]
            elif 'wednesdaysleep' in e[0]:
                Weekdays[3]['sleep'] = e[1]
            elif 'fridaysleep' in e[0]:
                Weekdays[4]['sleep'] = e[1]
            elif 'saturdaysleep' in e[0]:
                Weekdays[5]['sleep'] = e[1]
            elif 'sundaysleep' in e[0]:
                Weekdays[6]['sleep'] = e[1]
                
        StockExchanges = []
        for entry in stockexchangesList:
            e = entry.split(" = ")
            StockExchanges.append(e[1])
        KeyWords = []
        
        for entry in keywordsList:
            e = entry.split(" = ")
            KeyWords.append(e[1])
        
        MinorKeyWords = []
        for entry in minorkeywordsList:
            e = entry.split(" = ")
            MinorKeyWords.append(e[1])
        
    
    else:
        print("Creating config file...")
        config.read(filename)
        config.add_section('main')
        config.set('main','active',str(Active))
        config.set('main','StartTimeSeek',str(StartTimeSeek))
        config.set('main','Frequency',str(Frequency))
        config.set('main','SearchDepth',str(SearchDepth))
        config.add_section('stockexchanges')
        for i in range(0,len(StockExchanges)):
            config.set('stockexchanges',str(i),str(StockExchanges[i]))
        config.add_section('weekdays')
        for i in range(0,len(Weekdays)):
            config.set('weekdays',"{}{}".format(Weekdays[i]["name"],"active"), str(Weekdays[i]["active"]))
            config.set('weekdays',"{}{}".format(Weekdays[i]["name"],"wake"), str(Weekdays[i]["wake"]))
            config.set('weekdays',"{}{}".format(Weekdays[i]["name"],"sleep"), str(Weekdays[i]["sleep"]))
        config.add_section('skipdays')
        for i in range(0,len(SkipDays)):
            config.set('skipdays',str(i),str(SkipDays[i]))
        config.add_section('keywords')
        for i in range(0,len(KeyWords)):
            config.set('keywords',str(i),str(KeyWords[i]))
        config.add_section('minorkeywords')
        for i in range(0,len(MinorKeyWords)):
            config.set('minorkeywords',str(i),str(MinorKeyWords[i]))
        with open('config.ini', 'w') as f:
            config.write(f)
    
    

    

            
    
main()






