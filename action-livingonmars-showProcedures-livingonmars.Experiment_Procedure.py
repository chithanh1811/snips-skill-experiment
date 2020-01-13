#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hermes_python.hermes import Hermes
import requests
import json
import random
import subprocess
import re

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_CANCEL = "livingonmars:cancelProcedure"
INTENT_CONFIRM = "livingonmars:confirmProcedure"
INTENT_CHOOSE = "livingonmars:chooseProcedure"
INTENT_RANDOM = "livingonmars:randomizeProcedure"
INTENT_SHOW = "livingonmars:showProcedures"

# addresses for connections to the DB and GUI API servers 
DB_ADDR = "http://localhost:8000"
GUI_ADDR = "http://localhost:4040"

# check if HDMI is connected and set the global variable
cmd = ['tvservice', '-s']
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
o, e = proc.communicate()
isConnected = re.search("state 0x.*a", o.decode('ascii'))
print(isConnected)

# save the selected procedure
selectedProcedure = -1

########### STAGE ONE - LIST & SELECT PROCEDURES ###########
# TODO: Remove session. I renamed - hope it doesn't break anything
# action fuction for the START EXPERIMENT intent

def show_procedures(hermes, intent_message):
    print("The user is asking to show the experiment list")
    outputMessage = proceduresListOutput()
    return hermes.publish_continue_session(intent_message.session_id, outputMessage, [INTENT_CANCEL, INTENT_CHOOSE])

# TODO: open session here
# action fuction for the CHOOSE PROCEDURE intent
def choose_procedure(hermes, intent_message):
    print("The user is choosing a procedure")
    
    # get procedures data from the DB API
    procedures = requests.get(DB_ADDR + "/procedures").json()

    # get what the user said
    raw_choice = intent_message.slots.procedure.first().value

    # check and save which number was said
    if raw_choice == "one":
        choice = 1
    elif raw_choice == "two":
        choice = 2
    elif raw_choice == "three":
        choice = 3
    elif raw_choice == "four":
        choice = 4
    elif raw_choice == "five":
        choice = 5
    elif raw_choice == "six":
        choice = 6
    else:
        return hermes.publish_continue_session(intent_message.session_id, "Please select a number!", [INTENT_CHOOSE])
    
    # set the selected procedure
    global selectedProcedure
    selectedProcedure = choice

    # decide the output according to the version (VUI or VUI+GUI)
    outputMessage = "You selected {}, {}. Is that correct?".format(str(choice), str(procedures[choice-1]["title"])) 
    if isConnected:
        # request to GUI API to highlight the selected procedure
        r = requests.post(GUI_ADDR + "/select", json = {'id': choice})
  
    return hermes.publish_continue_session(intent_message.session_id, outputMessage, [INTENT_CONFIRM, INTENT_CANCEL])



########### STAGE TWO - PROCEDURE DETAIL ###########


# action function that handles the response of the session of the CHOOSE PROCEDURE intent
def confirm_procedure(hermes, intent_message):
    print("The user is confirming the chosen procedure")

    # get what the user said
    raw_choice = intent_message.slots.confirmation.first().value
    
    # check if it's yes and we know the number of the selected procedure
    global selectedProcedure
    if raw_choice == "yes" and selectedProcedure != -1:
       
        # request to the DB API to get the procedure detail
        procedure = requests.get(DB_ADDR + "/procedures/" + selectedProcedure).json()

        # decide the output according to the version (VUI or VUI+GUI)
        outputMessage = ""
        if isConnected:
            # create dialogue output for VUI+GUI
            outputMessage = ""
            # request to GUI API to show the procedure detail
        else:
            # create dialogue output for VUI
            outputMessage = ""
        
        return hermes.publish_end_session(intent_message.session_id, outputMessage)
    else:
        # user didn't confirm so the system resets
        outputMessage = proceduresListOutput()
        return hermes.publish_continue_session(intent_message.session_id, outputMessage, [INTENT_CHOOSE, INTENT_CANCEL])

def cancel_procedure(hermes, intent_message):
    print("The user is asking to cancel the request")
    r = requests.post(GUI_ADDR + "/cancel", json = {'cancel': 'true'})
    return hermes.publish_end_session(intent_message.session_id, "You cancelled the request")

########### "PRIVATE" METHODS ###########
# auxiliary function to execute all the necessary steps to list procedures
# returns the STRING outputMessage

def proceduresListOutput():
    # get procedures data from the DB API
    procedures = requests.get(DB_ADDR + "/procedures").json()

    # create the list of procedures with the order number from the JSON
    totalProcedures = 0
    order_number = 0
    procedureList = ""
    for procedure in procedures:
        order_number += 1
        totalProcedures += 1
        procedureList += str(order_number) + ". " + procedure["title"] + ". "

    # decide the output according to the version (VUI or VUI+GUI)
    outputMessage = ""
    if isConnected:
        # create dialogue output for VUI+GUI
        outputMessage = "I have found {} Procedures. Here are the procedures.".format(totalProcedures)
        # request to GUI API to show the list on the screen
        r = requests.post(GUI_ADDR + "/show", json = procedures)
    else:
        # create dialogue output for VUI
        outputMessage = "I have found {} Procedures. You can wake me up and tell me the number to choose a procedure. To listen to the information again, tell me to REPEAT. At any time of the procedure, you can ask me to CANCEL to exit. Here are the procedures: {} ".format(totalProcedures, procedureList)

    return outputMessage

###########

########### not necessary atm

def randomize_procedure(hermes, intent_message):
    print("The user is asking to start a random experiment")
    return hermes.publish_continue_session(intent_message.session_id, "randomize", [INTENT_CONFIRM])

###########

########### Hermes subscription - not sure why it's needed

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedures) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_RANDOM, randomize_procedure) \
        .start()

###########