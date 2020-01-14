#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hermes_python.hermes import Hermes
import requests
import json
import random
import subprocess
import time
import re

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_CANCEL = "livingonmars:cancelProcedure"
INTENT_CONFIRM = "livingonmars:confirmProcedure"
INTENT_CHOOSE = "livingonmars:chooseProcedure"
INTENT_SHOW = "livingonmars:showProcedures"
INTENT_FINISH = "livingonmars:finishProcedure"

# addresses for connections to the DB and GUI API servers 
DB_ADDR = "http://localhost:8000"
GUI_ADDR = "http://localhost:4040"

# save the selected procedure, start at 1
selectedProcedure = 0

# save the current step, start at 1
currentStep = 0

# save the current state
STATE = 0 
STAGE = 0

# triggered when "livingonmars:showProcedures" is detected
def show_procedures(hermes, intent_message):
    if STAGE == 0 and STATE == 0:
        # Go to STATE 1.1: Listing Available Procedure
        STAGE = 1
        STATE = 1
        print("STATE 1.1: Listing Available Procedure")
        output_message = proceduresListOutput()
        return hermes.publish_end_session(intent_message.session_id, output_message)
    if STAGE == 1 and STATE == 3:
        # Go to STATE 2.1: Starting the Selected Experiment - Listing Ingredients
        STAGE = 2
        STATE = 1
        print("STATE 2.1: Starting the Selected Experiment - Listing Ingredients")
    
    # TODO REPEAT()
    # TODO Manuals

# triggered when "livingonmars:chooseProcedure" is detected
def choose_procedure(hermes, intent_message):
    if STAGE == 1 and STATE == 1:
        # Go to STATE 1.2: Selecting a Procedure
        STAGE = 1
        STATE = 2
        print("STATE 1.2: Selecting a Procedure")

        # get procedures data from the DB API
        procedures = requests.get(DB_ADDR + "/procedures").json()

        # get what the user said and select the corresponding value
        raw_choice = intent_message.slots.procedure.first().value
        if raw_choice == "one":
            selectedProcedure = 1
        elif raw_choice == "two":
            selectedProcedure = 2
        elif raw_choice == "three":
            selectedProcedure = 3
        elif raw_choice == "four":
            selectedProcedure = 4
        elif raw_choice == "five":
            selectedProcedure = 5
        elif raw_choice == "six":
            selectedProcedure = 6
        else:
            return hermes.publish_continue_session(intent_message.session_id, "Please select a number from one to six!", [INTENT_CHOOSE, INTENT_CANCEL])
            # TODO Test this. Changed from end_session to continue_session, so that the user can reselect once the wrong input is detected.
        
        output_message = "You selected {}, {}. Is that correct?".format(str(selectedProcedure), str(procedures[selectedProcedure - 1]["title"]))

        # decide the output according to the version (VUI or V+GUI)
        # request to GUI API to highlight the selected procedure
        if isConnected():
            r = requests.post(GUI_ADDR + "/select", json={'id': selectedProcedure})

        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM, INTENT_CANCEL])
    
    # TODO Manuals

# triggered when "livingonmars:confirmProcedure" is detected
def confirm_procedure(hermes, intent_message):
    if STAGE == 1 and STATE == 2:
        # Go to STATE 1.3: Confirming the Selection
        STAGE = 1
        STATE = 3
        print("STATE 1.3: Confirming the Selection")

        # get what the user said
        raw_choice = intent_message.slots.confirmation.first().value

        # check if it's yes and we know the number of the selected procedure
        if raw_choice == "yes" and selectedProcedure != -1:
            print("Procedure " + str(selectedProcedure) + " confirmed")
            
            # request to the DB API to get the procedure detail
            procedure = requests.get(DB_ADDR + "/procedures/" + str(selectedProcedure)).json()
            resources_list = ""
            procedure_title = procedure["procedure"]["title"]
            for resource in procedure["resources"]:
                resources_list += resource["title"] + ", "

            output_message = "Got it! Here is procedure {}. Let me know when you're ready to start. For this procedure you will need: {}".format(procedure_title, resources_list)
            # decide the output according to the version (VUI or V+GUI)
            # create dialogue output for V+GUI    
            if isConnected():
                # TODO request to GUI API to show the procedure detail
                # CHANGE THIS
                r = requests.post(GUI_ADDR + "/select", json={'id': selectedProcedure})

            # return hermes.publish_end_session(intent_message.session_id, output_message)
        else:
            # user didn't confirm so the system resets
            # Go to STATE 1.1: Listing Available Procedure
            STAGE = 1
            STATE = 1
            print("STATE 1.1: Listing Available Procedure")
            output_message = proceduresListOutput()
            return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:cancelProcedure" is detected
def cancel_procedure(hermes, intent_message):
    # TODO Disable the default Cancel command, so that we can apply our custom actions (reset our parameters)
    # https://docs.snips.ai/articles/platform/dialog/multi-turn-dialog/disable-safe-word 
    print("The user is asking to cancel the request")
    STAGE = 0
    STATE = 0
    selectedProcedure = 0
    currentStep = 0
    r = requests.post(GUI_ADDR + "/cancel", json={'cancel': 'true'})
    return hermes.publish_end_session(intent_message.session_id, "You cancelled the request")

# triggered when "livingonmars:chooseProcedure" is detected
def finish_procedure(hermes, intent_message):
    if STAGE == 3 and STATE == 2:
        # Go to STATE 3.3: Finishing the Procedure
        STAGE = 1
        STATE = 3
        print("STATE 3.3: Finishing the Procedure")
        output_message = "Very good! You have finished the procedure. Returning to the start screen."
        
        if isConnected():
            # send request to GUI API to show the finish screen
            r = requests.get(GUI_ADDR + "/finish")
            
        return hermes.publish_end_session(intent_message.session_id, output_message)
    # TODO Manuals

# auxiliary function to execute all the necessary steps to list procedures
# returns the STRING outputMessage
def proceduresListOutput():
    # get procedures data from the DB API
    procedures = requests.get(DB_ADDR + "/procedures").json()

    # create the list of procedures with the order number from the JSON
    total_procedures = 0
    order_number = 0
    procedure_list = ""
    for procedure in procedures:
        order_number += 1
        total_procedures += 1
        procedure_list += str(order_number) + ". " + procedure["title"] + ". "

    # decide the output according to the version (VUI or VUI+GUI)
    output_message = ""
    global isConnected
    if isConnected:
        # create dialogue output for VUI+GUI
        output_message = "I have found {} Procedures. Here are the procedures.".format(total_procedures)
        # request to GUI API to show the list on the screen
        r = requests.post(GUI_ADDR + "/show", json=procedures)
    else:
        # create dialogue output for VUI
        output_message = "I have found {} Procedures. You can wake me up and tell me the number to choose a procedure. To listen to the information again, tell me to REPEAT. At any time of the procedure, you can ask me to CANCEL to exit. Here are the procedures: {} ".format(
            total_procedures, procedure_list)

    return output_message

# returns True if HDMI is connected
def isConnected():
    cmd = ['tvservice', '-s']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = proc.communicate()
    return re.search("^state 0x.*a$", o.decode('ascii'))

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedures) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_FINISH, finish_procedure) \
        .start()

# TODO Manual, Repeat, Start, Next