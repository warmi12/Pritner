from idlelib.iomenu import encoding

import cv2
import serial
import numpy as np
import time
import os
import floyd_steinberg_dithering
from os.path import exists
import pyttsx3
import threading
import random
from playsound import playsound

###PRINTER CMDS###
setPosition = bytearray(b'\x1B\x1D\x50\x33\x00\x00\x00\x00\x80\x02\xAA\x03')
startStopDocument = bytearray(b'\x1B\x1D\x03\x04\x00\x00\x1B\x1D\x03\x03\x00\x00')
feed = bytearray(b'\x1B\x4A\x18')
cut = bytearray(b'\x1D\x56\x41\x00')
stopDocument = bytearray(b'\x1B\x1D\x03\x04\x00\x00')
invertedPrintingEnable = bytearray(b'\x1D\x42\x01')
invertedPrintingDisable = bytearray(b'\x1D\x42\x00')
largeLettersEnable = bytearray(b'\x1B\x21\x10')
largeLettersDisable = bytearray(b'\x1B\x21\x00')
resetLeftMargin = bytearray(b'\x1D\x4C\x48\x00')
setCodePage = bytearray(b'\x1B\x1D\x74\x05')


try:
    ser = serial.Serial('COM3', 115200)
    serArdu = serial.Serial("COM20", 9600, timeout=.1)
    time.sleep(2) #time for arduino -> every com port open = restart ardu
except:
    print("SerialPortError")
    exit(1)

def binarizeImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th, img = cv2.threshold(img, 180, 1, cv2.THRESH_OTSU)
    return img

def replaceValues(img): #for printer 1 is black is 0 is white
    for i in range(0, img.shape[0]):  # changing 1 into 0 and 0 into 1
        for j in range(0, img.shape[1]):
            img[i][j] = 1 - img[i][j]
    return img

def calculateRows(img): #printer needs a multiple of 24 rows
    mod = img.shape[0] % 24  # checking how many rows should be added to the array
    if mod != 0:
        appendRows = 24 - mod
    else:
        appendRows = 0

    return appendRows

def alignImgRows(img, appendRows): #adding rows to scaled img (zeros = white) -> required for the draw command
    img_aligned = np.concatenate((img, np.zeros((appendRows, img.shape[1]), dtype=int)), axis=0)
    return img_aligned

def alignImgColumns(img): #adding columns -> centering img on the paper
    #maximum values for printer:
    #width = 568
    #height = 853
    if img.shape[1]<568:
        appendColumns = 284 - int((img.shape[1]/2))
        img_aligned = np.concatenate((np.zeros((img.shape[0], appendColumns), dtype=int),img), axis=1)
        return img_aligned
    else:
        return img

def createCmd(img): #transform img into printer cmd
    cmd=[]
    imgWidth = img.shape[1].to_bytes(2, 'little')

    for i in range(0, int(img.shape[0]/24)):
        img_flatten=img[i*24:((i+1)*24), :].flatten(order='F')
        #draw image cmd
        cmd.append(27) #change to hex
        cmd.append(42)
        cmd.append(33)
        cmd.append(imgWidth[0])
        cmd.append(imgWidth[1])
        for j in range(0, int(img_flatten.shape[0]/8)): #divide into bytes
            power = 7
            suma = 0
                                 #one bit = one pixel
                                 #10101010 = 0xAA = 170 = [black, white, ... so on]
                                 #2^7+2^5+2^3+2^1 = 170
            for k in range(0, 8):
                suma=suma+((2**power)*img_flatten[(j*8)+k])
                power=power-1
            cmd.append(suma)     #calculated value
        #line feed cmd
        cmd.append(27) #change to he
        cmd.append(74)
        cmd.append(24)

    return cmd


def largeInvertedEnable():
    ser.write(invertedPrintingEnable)
    ser.write(largeLettersEnable)

def largeInvertedDisable():
    ser.write(invertedPrintingDisable)
    ser.write(largeLettersDisable)

def dithering(imgName,scale): #if not exist do dithering
    if not exists("F:\\Printer\\finalPrinterProject\\pictures\\" + imgName + "_dithering.png"):
        floyd_steinberg_dithering.floyd_steinberg_combined(scale,imgName)

def printImg(imgName):
    #prepare img
    #dithering is necessary to display black and white imgs
    img = cv2.imread("F:\\Printer\\finalPrinterProject\\pictures\\"+imgName+"_dithering.png")
    img = binarizeImg(img)
    img = replaceValues(img)
    rows = calculateRows(img)
    img = alignImgRows(img, rows)
    img = alignImgColumns(img)
    #prepare cmd
    cmd = createCmd(img)

    #print img
    ser.write(startStopDocument)
    ser.write(cmd)
    ser.write(feed)
    ser.write(stopDocument)

#print img steps:
#read img
#scale img scaleImg()
#binarize img
#replace 1 to 0 and reverse
#add necessary rows
#align img
#create cmd
#send 1 start stop cmd, 2 cmd, 3 feed, 4 cut?, 5 stop

def readFile(file,fTruncate=1):
   if os.stat(file).st_size > 0:
        f = open(file, "r", encoding='cp852')
        lines = f.readlines()
        if fTruncate==1: #cleaning the file
            f = open(file, "w")
            f.truncate()
        f.close()
        return lines

def setMargin(length): #setting the margin of letters
    value = int(12 * length) #one letter = 12points width
    if value<568:
        value = int((568-value)/2) #calculate value of margin
    else:
        value=0

    value = value.to_bytes(2, 'little')
    cmd=[]
    cmd.append(29) #margin cmd -> change to hex
    cmd.append(76)
    cmd.append(value[0])
    cmd.append(value[1])
    ser.write(cmd)

def printGift(giftInfo):
    gifter = bytearray("  "+ giftInfo[0] + "  \n",encoding = 'cp852') #encoded Polish characters
    gift = bytearray(" Wysłał "+ giftInfo[1]+ "  \n",encoding = 'cp852')

    largeInvertedEnable()
    setMargin(len(gifter) - 3)
    ser.write(gifter)
    setMargin(len(gift) - 3)
    ser.write(gift)

def printLine():
    ser.write(resetLeftMargin)
    ser.write(b'\n=========================================\n')

def printCommLine():
    ser.write(resetLeftMargin)
    ser.write(b'\n================KOMENTARZ================\n')

def speak(text):
    text=str(text)
    engine.say(text)
    engine.runAndWait()

def replaceCharAtIndex(orgStr, index, replacement):
    newStr = orgStr
    if index < len(orgStr):
        newStr = orgStr[0:index] + replacement + orgStr[index + 1:]
    return newStr

def prepareWord(word):
    cover = int(round(len(word) * 0.4)) #cover ~40% the letters
    indextab = [] #index of covered letters
    counter = 0

    while counter < cover+1:
        index = random.randint(0, len(word))
        if index not in indextab:
            indextab.append(index)
            counter = counter + 1
            # zastap te litere
            word = replaceCharAtIndex(word, index, "*")

    offset = 15 - len(word) #offset for 16x2 lcd
    word=' '*offset + word
    print(word)

    return word.upper()


#arduino variables
counter=0
arduDisplayWord=''

def arduinoDisplay():
    threading.Timer(1.0, arduinoDisplay).start() #run this fun every 1 sec
    global counter
    global queueValue
    global arduDisplayWord

    if (counter == 0):
        #show message for 5 seconds
        serArdu.write(bytes('s' + '\n', "UTF-8")) #special cmd for arduino
        counter = counter + 1
    elif counter == 6:
        #show the word to guess
        counter = counter + 1
        serArdu.write(bytes('w'+arduDisplayWord+'\n', "UTF-8"))
    else:
        if counter<26:
            counter=counter+1
        else:
            counter=0


if __name__ == '__main__':
    commentsList = []
    giftList=[]
    speakerList = []
    wordsList=[]

    #get the first word to guess
    wordsList = readFile("words.txt")
    word = wordsList.pop(0)
    word=word.strip('\n')
    arduDisplayWord = prepareWord(word)
    arduinoDisplay() #run arduino cycle

    #init engine
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # for voice in voices:
    #     print("Voice: %s" % voice.name)
    #     print(" - ID: %s" % voice.id)
    #     print(" - Languages: %s" % voice.languages)
    #     print(" - Gender: %s" % voice.gender)
    #     print(" - Age: %s" % voice.age)
    #     print("\n")
    engine.setProperty('rate', 125)
    engine.setProperty("voice", voices[0].id)

    ser.write(setCodePage)

    while True:
        if not giftList: #list empty -> read file
            giftList = readFile("gift.txt")
        elif len(giftList) > 0:
            nick=giftList.pop(0)

            nick = nick.strip('\n')
            nick = nick.split(",")

            if exists("F:\\Printer\\finalPrinterProject\\pictures\\" + nick[0] + ".png"):
                dithering(nick[0],400)
                printImg(nick[0])

                ser.write(setCodePage) #setting every print

                printGift(nick)

                dithering("thank",110) #should be done only once
                printImg("thank")

                ser.write(setCodePage)

                printLine()
                ser.write(b'\n')
                ser.write(b'\n')
                ser.write(b'\n')

                speak(str(nick[0] + " wysłał, " + nick[1] + "\n"))

        if not commentsList:
            commentsList = readFile("comment.txt")
        elif len(commentsList) > 0:
            comment = commentsList.pop(0)

            comment = comment.strip('\n')
            comment = comment.split("[")

            if comment[1].lower() == word.lower(): #A condition checking if the word has been guessed
                counter = 0 #arduino counter

                #prepare message
                printLine()
                gz = bytearray(b" GRATULACJE!!! \n")
                printWinner =bytearray(" " + comment[0] + " zgadł słowo! \n", encoding='cp852')
                printWordResult = bytearray(" rozwiązanie to: " + word + " \n", encoding='cp852')

                #Printing win message
                largeInvertedEnable()

                setMargin(len(gz) - 3)
                ser.write(gz)

                setMargin(len(printWinner) - 3)
                ser.write(printWinner)

                setMargin(len(printWordResult) - 3)
                ser.write(printWordResult)


                #disble large letters and print line
                largeInvertedDisable()
                printLine()
                # print empty lines -> change
                ser.write(b'\n')
                ser.write(b'\n')
                ser.write(b'\n')
                ser.write(b'\n')
                ser.write(b'\n')

                #playsound("F:\\Printer\\finalPrinterProject\\
                speak('BRAWO!BRAWO!BRAWO!')
                #speaker

                #display next word
                word = wordsList.pop(0)
                word = word.strip('\n')
                arduDisplayWord = prepareWord(word)

            else:
                #incorrect -> print comment
                printCommLine()
                userCommentInfo = bytes(comment[0] + ": " + comment[1] + " \n", encoding='cp852')
                ser.write(userCommentInfo)







