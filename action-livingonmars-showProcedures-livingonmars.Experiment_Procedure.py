#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hermes_python.hermes import Hermes
import requests
import json
import random
import subprocess
import time

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_CANCEL = "livingonmars:cancelProcedure"
INTENT_CONFIRM = "livingonmars:confirmProcedure"
INTENT_CHOOSE = "livingonmars:chooseProcedure"
INTENT_SHOW = "livingonmars:showProcedures"
INTENT_START = "livingonmars:startProcedure"
INTENT_NEXT = "livingonmars:nextStep"
INTENT_FINISH = "livingonmars:finishProcedure"
INTENT_REPEAT = "livingonmars:repeat"
INTENT_HELP = "livingonmars:help"


# addresses for connections to the DB and GUI API servers 
DB_ADDR = "http://localhost:8000"
GUI_ADDR = "http://localhost:4040"

# save the procedures list
procedures_list = ""

# save the selected procedure, start at 1
selected_procedure = 0
selected_procedure_title = ""
resources_list = ""

# save the steps data
current_step = -1
procedure_steps = None
total_steps = -1

# save the current state
STATE = 0 
STAGE = 0

# triggered when "livingonmars:showProcedures" is detected
def show_procedures(hermes, intent_message):
    global STAGE, STATE
    if STAGE == 0 and STATE == 0:
        # Go to STATE 1.1: Listing Available Procedure
        STAGE = 1
        STATE = 1
        print("STATE 1.1: Listing Available Procedure")
        output_message = proceduresListOutput()
        return hermes.publish_end_session(intent_message.session_id, output_message)
    if STAGE == 1 and STATE == 3:
        # Go to STATE 2.1: Showing Procedure Overview
        STAGE = 2
        STATE = 1
        print("STATE 2.1: Showing Procedure Overview")

        # The index for the current step. We are always starting with the first step (0 in an array)
        current_step = 1

        # Getting the steps for the selected procedure from the Database
        procedure_steps = requests.get(DB_ADDR + "/proceduresteps/" + str(selected_procedure)).json()

        # Getting the instructions for the first step
        first_step = procedure_steps["steps"][current_step-1]["description"]
        output_message = "Alright! This is the first step. When you are ready for the next step, please say next step! Let's start! {} ".format(first_step)

        if isConnected():
            # Sending the instructions to the GUI
            r = requests.post(GUI_ADDR + "/start")

        return hermes.publish_end_session(intent_message.session_id, output_message)
    
    # TODO REPEAT()
    # TODO Manuals

# triggered when "livingonmars:chooseProcedure" is detected
def choose_procedure(hermes, intent_message):
    global STAGE, STATE, selected_procedure
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
            selected_procedure = 1
        elif raw_choice == "two":
            selected_procedure = 2
        elif raw_choice == "three":
            selected_procedure = 3
        elif raw_choice == "four":
            selected_procedure = 4
        elif raw_choice == "five":
            selected_procedure = 5
        elif raw_choice == "six":
            selected_procedure = 6
        else:
            return hermes.publish_end_session(intent_message.session_id, "Please select a number from one to six!")
            # TODO Test this. Changed from end_session to continue_session, so that the user can reselect once the wrong input is detected.
        
        output_message = "You selected {}, {}. Is that correct?".format(str(selected_procedure), str(procedures[selected_procedure - 1]["title"]))

        # decide the output according to the version (VUI or V+GUI)
        # request to GUI API to highlight the selected procedure
        if isConnected():
            r = requests.post(GUI_ADDR + "/select", json={'id': selected_procedure})

        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM, INTENT_CANCEL])
    
    # TODO Manuals

# triggered when "livingonmars:confirmProcedure" is detected
def confirm_procedure(hermes, intent_message):
    global STAGE, STATE, selected_procedure, total_steps
    if STAGE == 1 and STATE == 2:
        # Go to STATE 2.1: Confirming the Selection & Listing the Ingredients
        STAGE = 2
        STATE = 1
        print("STATE 2.1: Confirming the Selection & Listing the Ingredients")

        # get what the user said
        raw_choice = intent_message.slots.confirmation.first().value

        # check if it's yes and we know the number of the selected procedure
        if raw_choice == "yes" and selected_procedure != -1:
            print("Procedure " + str(selected_procedure) + " confirmed")

            # request to the DB API to get the procedure detail
            procedure = requests.get(DB_ADDR + "/procedures/" + str(selected_procedure)).json()
            resources_list = ""
            procedure_title = procedure["procedure"]["title"]
            total_steps = procedure["stepsCount"]
            for resource in procedure["resources"]:
                resources_list += resource["title"] + ", "

            output_message = "Got it! Here is procedure {}. It has {} steps. Let me know when you're ready to start. For this procedure you will need: {}".format(
                procedure_title, total_steps, resources_list)
            # decide the output according to the version (VUI or V+GUI)
            # create dialogue output for V+GUI
            if isConnected():
                # TODO request to GUI API to show the procedure detail
                # CHANGE THIS
                r = requests.post(GUI_ADDR + "/confirm", json=procedure)

            return hermes.publish_end_session(intent_message.session_id, output_message)
        else:
            # user didn't confirm so the system resets
            # Go to STATE 1.1: Listing Available Procedure
            STAGE = 1
            STATE = 1
            print("STATE 1.1: Listing Available Procedure")
            output_message = proceduresListOutput()
            # go back to procedure list
            r = requests.get(GUI_ADDR + "/cancel")
            return hermes.publish_end_session(intent_message.session_id, output_message)

# action function that handles the response of the session of the START PROCEDURE intent
def start_procedure(hermes, intent_message):
    global STAGE, STATE, current_step, procedure_steps
    if STAGE == 0 and STATE == 0:
        # Go to STATE 1.1: Listing Available Procedure
        STAGE = 1
        STATE = 1
        print("STATE 1.1: Listing Available Procedure")
        output_message = proceduresListOutput()
        return hermes.publish_end_session(intent_message.session_id, output_message)

    if STAGE == 2 and STATE == 1:
        # Go to STATE 3.1: Following the Steps
        STAGE = 3
        STATE = 1
        print("STATE 3.1: Following the Steps")

        # The index for the current step. We are always starting with the first step (0 in an array)
        current_step = 1

        # Getting the steps for the selected procedure from the Database
        procedure_steps = requests.get(DB_ADDR + "/proceduresteps/" + str(selected_procedure)).json()

        # Getting the instructions for the first step
        first_step = procedure_steps["steps"][current_step - 1]["description"]
        output_message = "Alright! This is the first step. When you are ready for the next step, please say next step! Let's start! {} ".format(
            first_step)

        if isConnected():
            # Sending the instructions to the GUI
            r = requests.post(GUI_ADDR + "/showstep", json=procedure_steps["steps"][current_step - 1])

        return hermes.publish_end_session(intent_message.session_id, output_message)

# action function that handles the response of the session of the NEXT STEP intent
def next_step(hermes, intent_message):
    global STAGE, STATE, total_steps, current_step, procedure_steps

    # increase the current step to move to the next
    current_step += 1

    # get the description of the next step from the list
    next_step_description = procedure_steps["steps"][current_step - 1]["description"]

    if STAGE == 3 and STATE == 1:
        # Check if the current step is the last step
        if current_step == total_steps:
            # Go to STATE 3.2: The Last Step
            STATE = 2
            print("STATE 3.2: Last Step")
            output_message = "You are almost done! This is the last step. Please tell me when you are done. The last step is {}".format(
                next_step_description)
        else:
            # Stay in STATE 3.1: Following the Steps
            print("STATE 3.1: Following the Steps")
            print("STEP {}".format(current_step))
            output_message = "This is step {} out of {}. {}".format(current_step, total_steps, next_step_description)

    if isConnected():
        # Sending the instructions to the GUI
        r = requests.post(GUI_ADDR + "/showstep", json=procedure_steps["steps"][current_step - 1])

    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:chooseProcedure" is detected
def finish_procedure(hermes, intent_message):
    global STAGE, STATE
    if STAGE == 3 and STATE == 2:
        # Go to STATE FINALE: Finishing the Procedure
        print("STATE FINALE: Finishing the Procedure")
        STAGE = 0
        STATE = 0
        print("STATE 0.0: Initial")
        output_message = "Very good! You have finished the procedure. Returning to the start screen."
        
        if isConnected():
            # send request to GUI API to show the finish screen
            r = requests.get(GUI_ADDR + "/finish")
            
        return hermes.publish_end_session(intent_message.session_id, output_message)
    # TODO Manuals

# triggered when "livingonmars:repeat" is detected
def repeat(hermes, intent_message):
    print("Repeat intent triggered!")
    
    output_message = repeatMessageOutput()

    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:help" is detected
def help_intent(hermes, intent_message):
    print("Help intent triggered!")
    
    output_message = manualMessageOutput()
    
    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:cancelProcedure" is detected
def cancel_procedure(hermes, intent_message):
    # TODO Disable the default Cancel command, so that we can apply our custom actions (reset our parameters)
    # https://docs.snips.ai/articles/platform/dialog/multi-turn-dialog/disable-safe-word 
    
    global STAGE, STATE, procedures_list, selected_procedure, selected_procedure_title, resources_list, current_step, procedure_steps, total_steps
    print("STATE 0.0: Initial")
    
    # reset all global variables
    STATE = 0
    STAGE = 0
    procedures_list = ""
    selected_procedure = 0
    selected_procedure_title = ""
    resources_list = ""
    current_step = -1
    procedure_steps = None
    total_steps = -1

    r = requests.post(GUI_ADDR + "/cancel", json={'cancel': 'true'})
    return hermes.publish_end_session(intent_message.session_id, "You cancelled the request")

# auxiliary function to execute all the necessary steps to list procedures
# returns the STRING outputMessage
def proceduresListOutput():
    # get procedures data from the DB API
    procedures = requests.get(DB_ADDR + "/procedures").json()

    # create the list of procedures with the order number from the JSON
    total_procedures = 0
    order_number = 0
    global procedures_list
    for procedure in procedures:
        order_number += 1
        total_procedures += 1
        procedures_list += str(order_number) + ". " + procedure["title"] + ". "

    # decide the output according to the version (VUI or VUI+GUI)
    output_message = ""
    if isConnected():
        # create dialogue output for VUI+GUI
        output_message = "I have found {} Procedures. Here are the procedures.".format(total_procedures)
        # request to GUI API to show the list on the screen
        r = requests.post(GUI_ADDR + "/show", json=procedures)
    else:
        # create dialogue output for VUI
        output_message = "I have found {} Procedures. You can wake me up and tell me the number to choose a procedure. To listen to the information again, tell me to REPEAT. At any time of the procedure, you can ask me to CANCEL to exit. Here are the procedures: {} ".format(
            total_procedures, procedure_list)

    return output_message

# auxiliary function to get the output messages for each STAGE and STATE
def repeatMessageOutput():
    global STAGE, STATE, procedures_list, selected_procedure_title, total_steps, resources_list, current_step, procedure_steps
    
    output_message = "I don't remember what I just said either... Sorry..."

    # get the message for the stage and state
    if STAGE == 1 and STATE == 1:
        print("Repeating message for: STATE 1.1")
        output_message = "You can wake me up and tell me the number to choose a procedure. Here are the procedures: {}".format(procedures_list)
    
    if STAGE == 2 and STATE == 1:
        print("Repeating message for: STATE 2.1")
        output_message = "Let me know when you're ready to start the procedure {}. It has {} steps. You will need: {}".format(selected_procedure_title, total_steps, resources_list)
    
    if STAGE == 3 and STATE == 1:
        next_step_description = procedure_steps["steps"][current_step-1]["description"]
        
        if current_step == 1:
            print("Repeating message for: STATE 3.1 and it's the first step")
            output_message = "When you are ready for the next step, please say next step! Let's start! {}".format(next_step_description)
        
        if current_step > 1 and current_step < total_steps:
            print("Repeating message for: STATE 3.1 and it's not the first step nor the last")
            output_message = "This is step {} out of {}. {}".format(current_step, total_steps, next_step_description)
        
    if STAGE == 3 and STATE == 2:
        next_step_description = procedure_steps["steps"][current_step-1]["description"]

        print("Repeating message for: STATE 3.2")
        output_message = "You are almost done! This is the last step. Please tell me when you are done. The last step is {}".format(next_step_description)

    return output_message

# auxiliary function to get the manual messages for each STAGE and STATE
def manualMessageOutput():
    global STAGE, STATE, total_steps, current_step
    
    output_message = "I am lost and I do not know what the hell we are doing either..."

    # get the message for the stage and state
    if STAGE == 0 and STATE == 0:
        print("Getting the manual for: STATE 0.0")
        output_message = "I am here to help you with lab tasks.. At anytime, you can call me by my name, and ask for help like you did now. Other things I can always do is to, repeat everything I say if you want to hear it again.. Right now, you can call me and say that you want to start an experiment!"
        
    if STAGE == 1 and STATE == 1:
        print("Getting the manual for: STATE 1.1")
        output_message = "You can wake me up and tell me the number to choose a procedure."
    
    if STAGE == 2 and STATE == 1:
        print("Getting the manual for: STATE 2.1")
        output_message = "Let me know when you're ready to start the procedure"
    
    if STAGE == 3 and STATE == 1:
        print("Getting the manual for: STATE 3.1")
        output_message = "When you are ready for the next step, please say next step!"
        
    if STAGE == 3 and STATE == 2:
        print("Getting the manual for: STATE 3.2")
        output_message = "You are almost done! This is the last step. Please tell me when you are done."

    return output_message

# returns True if HDMI is connected
def isConnected():
    #cmd = ['sudo', 'tvservice', '-s']
    #proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #o, e = proc.communicate()
    #return re.search("^state 0x.*a$", o.decode('ascii'))
    return True

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedures) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_START, start_procedure) \
        .subscribe_intent(INTENT_NEXT, next_step) \
        .subscribe_intent(INTENT_FINISH, finish_procedure) \
        .subscribe_intent(INTENT_REPEAT, repeat) \
        .subscribe_intent(INTENT_HELP, help_intent) \
        .start()

# TODO Manual
