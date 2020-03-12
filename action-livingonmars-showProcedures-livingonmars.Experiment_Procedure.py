#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hermes_python.hermes import Hermes
import requests
import json
import random
import subprocess
import time
from websocket import create_connection

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_CANCEL = "livingonmars:cancelProcedure"
INTENT_CONFIRM = "livingonmars:confirmProcedure"
INTENT_CHOOSE = "livingonmars:chooseProcedure"
INTENT_SHOW = "livingonmars:showProcedures"
INTENT_START = "livingonmars:startProcedure"
INTENT_NEXT = "livingonmars:nextStep"
INTENT_PREVIOUS = "livingonmars:previousStep"
INTENT_FINISH = "livingonmars:finishProcedure"
INTENT_REPEAT = "livingonmars:repeat"
INTENT_HELP = "livingonmars:help"
INTENT_CONFIRM_CANCEL = "livingonmars:confirmExit"
INTENT_HELLO = "livingonmars:hello"

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

# triggered when "livingonmars:hello" is detected
def hello(hermes, intent_message):
    global STAGE, STATE
    print("STATE 0.0: Initial")

    if STAGE == 0 and STATE == 0:
        send("Hello! I can help you with scientific experiments!@regular")
        #output_message = "Hello! I can help you with scientific experiments. Here is what I can do at any time. You can ask me to repeat. You can ask me to stop. Or you can ask me for help when you don't know what to do. If you want to do an experiment with me, call me after I finishe talking, and say, I want to do an experiment. Enjoy!"
    else:
        # get the default message for the current stage
        output_message = get_wrong_intent_message()

    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:showProcedures" is detected
def show_procedures(hermes, intent_message):
    global STAGE, STATE

    if STAGE == 0 and STATE == 0:
        # Go to STATE 1.1: Listing Available Procedure
        STAGE = 1
        STATE = 1
        print("STATE 1.1: Listing Available Procedure")

        # get the list of procedures and the dialogue output for VUI
        output_message = proceduresListOutput()

        return hermes.publish_end_session(intent_message.session_id, output_message)
    elif STAGE == 1 and STATE == 3:
        # Go to STATE 2.1: Showing Procedure Overview
        STAGE = 2
        STATE = 1
        print("STATE 2.1: Showing Procedure Overview")

        # get the procedure steps and the dialogue output for VUI
        output_message = get_procedure_steps()

        if isConnected():
            # Sending the instructions to the GUI
            r = requests.post(GUI_ADDR + "/start")

        return hermes.publish_end_session(intent_message.session_id, output_message)
    else:
        # get the default message for the current stage
        output_message = get_wrong_intent_message()
        return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:chooseProcedure" is detected
def choose_procedure(hermes, intent_message):
    global STAGE, STATE, selected_procedure, procedures

    if STAGE == 0 and STATE == 0:
        # Go to STATE 1.1: Listing Available Procedure
        STAGE = 1
        STATE = 1
        print("STATE 1.1: Listing Available Procedure")
        output_message = proceduresListOutput()
        return hermes.publish_end_session(intent_message.session_id,
                                          output_message)
    elif STAGE == 1 and STATE == 1:
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
            STATE = 1
            return hermes.publish_end_session(intent_message.session_id, "Sorry, I didn't get that. Please call me again, and select a number from one to six")
            # TODO Test this. Changed from end_session to continue_session, so that the user can reselect once the wrong input is detected.

        # create dialogue output for VUI
        output_message = "You selected {}, {}. Is this correct?".format(
            str(selected_procedure), # TODO bug here when DB is down??
            str(procedures[selected_procedure - 1]["title"]))

        if isConnected():
            # request to GUI API to highlight the selected procedure
            r = requests.post(GUI_ADDR + "/select",
                              json={'id': selected_procedure})

        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM])
    elif STAGE == 1 and STATE == 3:
        # Go to STATE 2.1: Starting the Selected Experiment - Listing Ingredients
        STAGE = 2
        STATE = 1
        print(
            "STATE 2.1: Starting the Selected Experiment - Listing Ingredients"
        )

    else:
        # get the default message for the current stage
        output_message = get_wrong_intent_message()
        return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:confirmProcedure" is detected
def confirm_procedure(hermes, intent_message):
    global STAGE, STATE, selected_procedure, total_steps, resources_list, selected_procedure_title

    # output message for wrong intent recognised or for a wrong answer that wasn't detected as YES or NO
    output_message = get_wrong_intent_message()

    # if we are at the right stage and any slot was detected (yes or no answer was matched)
    if STAGE == 1 and STATE == 2 and intent_message.slots.confirmation.first() != None:
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
            procedure = requests.get(DB_ADDR + "/procedures/" +
                                     str(selected_procedure)).json()
            resources_list = ""
            selected_procedure_title = procedure["procedure"]["title"]
            total_steps = procedure["stepsCount"]
            for resource in procedure["resources"]:
                resources_list += resource["title"] + ", "

            # create dialogue output for VUI
            output_message = "All right! Here is experiment {}. It has {} steps. Let me know, when you're ready to start. For this experiment, you will need. {}".format(
                selected_procedure_title, total_steps, resources_list)

            if isConnected():
                # request to GUI API to show the procedure detail
                r = requests.post(GUI_ADDR + "/confirm", json=procedure)

            return hermes.publish_end_session(intent_message.session_id, output_message)

        else:
            # user said no so the system goes back to the list
            # Go to STATE 1.1: Listing Available Procedure
            STAGE = 1
            STATE = 1
            print("STATE 1.1: Listing Available Procedure")
            output_message = get_repeat_message_output()

            if isConnected():
                # go back to procedure list
                r = requests.get(GUI_ADDR + "/confirm")

            return hermes.publish_end_session(intent_message.session_id, output_message)

    elif STAGE == 1 and STATE == 2 and intent_message.slots.confirmation.first() == None:
        # do the confirm again
        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM])

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
        return hermes.publish_end_session(intent_message.session_id,
                                          output_message)

    elif STAGE == 2 and STATE == 1:
        # Go to STATE 3.1: The First Step
        STAGE = 3
        STATE = 1
        print("STATE 3.1: The First Step")

        output_message = get_procedure_steps()

        if isConnected():
            # Sending the instructions to the GUI
            r = requests.post(GUI_ADDR + "/showstep",
                              json=procedure_steps["steps"][current_step - 1])

        return hermes.publish_end_session(intent_message.session_id,
                                          output_message)
    else:
        # get the default message for the current stage
        output_message = get_wrong_intent_message()
        return hermes.publish_end_session(intent_message.session_id,
                                          output_message)

# action function that handles the response of the session of the NEXT STEP intent
def next_step(hermes, intent_message):
    global STAGE, STATE, total_steps, current_step, procedure_steps

    # condition so that only at this stage the step related variables are updated
    if STAGE == 3 and (STATE == 1 or STATE == 2):
        # increase the current step to move to the next
        current_step += 1
        print("The current step is: " + str(current_step))
        # get the description of the next step from the list
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]

        if STATE == 1:
            # Go to STATE 3.2: Following the Steps
            STATE = 2
            print("STATE 3.2: Following the Steps")
            print("The current step is: " + str(current_step))
            output_message = "Here is step {}, out of {}. If you need to hear the previous step, tell me to go back. {}".format(
                current_step, total_steps, step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

        elif STATE == 2:
            # Check if the current step is the last step
            if current_step == total_steps:
                # Go to STATE 3.3: The Last Step
                STATE = 3
                print("STATE 3.3: Last Step")
                output_message = "You are almost done! Please tell me, when you are finished. The last step is. {}".format(
                    step_description)
            else:
                # Stay in STATE 3.2: Following the Steps
                print("STATE 3.2 - STEP {}".format(current_step))
                output_message = "Here is step, {}, out of, {}. {}".format(
                    current_step, total_steps, step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

    elif STAGE == 3 and STATE == 3:
        # Go to STATE FINALE: Finishing the Procedure
        print("STATE FINALE: Finishing the Procedure")
        STAGE = 0
        STATE = 0
        print("STATE 0.0: Initial")

        output_message = "That was the last step. Very good! You have finished the experiment. The session ends here. Let's go back to where we started."

        # reset all global variables
        procedures_list = ""
        selected_procedure = 0
        selected_procedure_title = ""
        resources_list = ""
        current_step = -1
        procedure_steps = None
        total_steps = -1

        if isConnected():
                # send request to GUI API to show the finish screen
                r = requests.get(GUI_ADDR + "/finish")

        return hermes.publish_end_session(intent_message.session_id,
                                              output_message)
    else:
        print("Stage {}.{} - Wrong intent detected.".format(STAGE, STATE))
        # get the default message for the current stage
        output_message = get_wrong_intent_message()

    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:previousStep" is detected
def previous_step(hermes, intent_message):
    global STAGE, STATE, total_steps, current_step, procedure_steps
    print("Previous Step triggered!")

    if STAGE == 3 and STATE == 1:
        print("STATE 3.1: The First Step - current step was not updated")
        output_message = "You are at the first step of the experiment."

    # condition so that only at this stage and states the step related variables are updated
    elif STAGE == 3 and (STATE == 2 or STATE == 3):
        # decrease the current step to go back
        current_step -= 1

        # get the description of the step from the list
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]

        # if previous step is the first one
        if current_step == 1:
            # Go to STATE 3.1: The First Step
            STATE = 1
            print("STATE 3.1: The First Step")
            output_message = "Alright! Here is the first step: {}".format(
                step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

        elif STATE == 2:
            # Stay in STATE 3.2: Following the Steps
            print("State 3.2 - STEP {}".format(current_step))
            output_message = "Here is the previous step. {}".format(step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

        elif STATE == 3:
            # Go back to STATE 3.2: Following the Steps
            STATE = 2
            print("State 3.3 - STEP {}".format(current_step))
            output_message = "Here is the previous step. {}".format(step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

    else:
        print("Stage {}.{} - Wrong intent detected.".format(STAGE, STATE))
        # get the default message for the current stage
        output_message = get_wrong_intent_message()

    return hermes.publish_end_session(intent_message.session_id, output_message)

# triggered when "livingonmars:chooseProcedure" is detected
def finish_procedure(hermes, intent_message):
    global STAGE, STATE, procedures_list, selected_procedure, selected_procedure_title, resources_list, current_step, procedure_steps, total_steps

    if STAGE == 3 and STATE == 3:
        # Go to STATE FINALE: Finishing the Procedure
        print("STATE FINALE: Finishing the Procedure")
        STAGE = 0
        STATE = 0
        print("STATE 0.0: Initial")

        output_message = "Very good! You have finished the experiment. The session ends here. Let's go back to where we started."

        # reset all global variables
        procedures_list = ""
        selected_procedure = 0
        selected_procedure_title = ""
        resources_list = ""
        current_step = -1
        procedure_steps = None
        total_steps = -1

        if isConnected():
            # send request to GUI API to show the finish screen
            r = requests.get(GUI_ADDR + "/finish")

        return hermes.publish_end_session(intent_message.session_id,
                                          output_message)
    elif STAGE == 3:
        # increase the current step to move to the next
        current_step += 1
        print("The current step is: " + str(current_step))

        # get the description of the next step from the list
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]

        if STATE == 1:
            # Go to STATE 3.2: Following the Steps
            STATE = 2
            print("STATE 3.2: Following the Steps")
            output_message = "Alright, but we are not at the last step yet, so here is the next step. To hear the previous step, tell me to go back. This is step {}, out of {}. {}".format(
                current_step, total_steps, step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

        elif STATE == 2:
            # Check if the current step is the last step
            if current_step == total_steps:
                # Go to STATE 3.3: The Last Step
                STATE = 3
                print("STATE 3.3: Last Step")
                output_message = "You are almost done! Please tell me, when you are finished. The last step is. {}".format(
                    step_description)
            else:
                # Stay in STATE 3.2: Following the Steps
                print("STATE 3.2 - STEP {}".format(current_step))
                output_message = "Alright, but we are not at the last step yet, so here is the next step. This is step {}, out of {}. {}".format(
                    current_step, total_steps, step_description)
            if isConnected():
                # Sending the instructions to the GUI
                r = requests.post(GUI_ADDR + "/showstep",
                                  json=procedure_steps["steps"][current_step - 1])

    else:
        print("Stage {}.{} - Wrong intent detected.".format(STAGE, STATE))
        # get the default message for the current stage
        output_message = get_wrong_intent_message()

    return hermes.publish_end_session(intent_message.session_id,
                                      output_message)

# triggered when "livingonmars:repeat" is detected
def repeat(hermes, intent_message):
    print("Repeat intent triggered!")

    output_message = get_repeat_message_output()

    return hermes.publish_end_session(intent_message.session_id,
                                      output_message)

# triggered when "livingonmars:help" is detected
def help_intent(hermes, intent_message):
    print("Help intent triggered!")

    output_message = get_manual_message_output()

    return hermes.publish_end_session(intent_message.session_id,
                                      output_message)

# triggered when "livingonmars:cancelProcedure" is detected
    # TODO Disable the default Cancel command, so that we can apply our custom actions (reset our parameters)
    # https://docs.snips.ai/articles/platform/dialog/multi-turn-dialog/disable-safe-word
def cancel_procedure(hermes, intent_message):

    output_message = "You are about to go back to where we started. Are you sure?"

    if isConnected():
        r = requests.get(GUI_ADDR + "/cancelconfirm")

    return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM_CANCEL])

# triggered when "livingonmars:confirmExit" is detected
def confirm_cancel(hermes, intent_message):
    global STAGE, STATE, procedures_list, selected_procedure, selected_procedure_title, resources_list, current_step, procedure_steps, total_steps

    # check if anything was detected and mapped to a slot
    if intent_message.slots.confirmation.first() != None:

        # get what the user said
        raw_choice = intent_message.slots.confirmation.first().value

        # check if it's yes
        if raw_choice == "yes":
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

            output_message = "I have stopped the session. We are now going back to the start."
            if isConnected():
                r = requests.post(GUI_ADDR + "/cancel", json={"cancel": True})

            return hermes.publish_end_session(intent_message.session_id, output_message)
        else:
            # the answer was no, so the system repeats the message of the current stage
            output_message = get_repeat_message_output()
            if isConnected():
                r = requests.post(GUI_ADDR + "/cancel", json={"cancel": False})

            return hermes.publish_end_session(intent_message.session_id, output_message)
    else:
        # the slot was empty so the system asks to confirm again
        output_message = "I didn't get that. You are about to go back to where we started. Are you sure?"
        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM_CANCEL])

# auxiliary function to execute all the necessary steps to list procedures
# returns the STRING outputMessage
def proceduresListOutput():
    global procedures_list

    # get procedures data from the DB API
    procedures = requests.get(DB_ADDR + "/procedures").json()

    # create the list of procedures with the order number from the JSON
    total_procedures = 0
    order_number = 0
    procedures_list = ""
    for procedure in procedures:
        order_number += 1
        total_procedures += 1
        procedures_list += str(order_number) + ". " + procedure["title"] + ". "

    # create dialogue output for VUI
    output_message = "I have found, {}, experiments. You can wake me up and tell me the number, of the experiment you want to select. Here are the experiments. {} ".format(
        total_procedures, procedures_list)

    if isConnected():
        # request to GUI API to show the list on the screen
        r = requests.post(GUI_ADDR + "/show", json=procedures)

    return output_message

# auxiliary function to get the procedures steps and the output message for the start procedure
# returns the STRING outputMessage
def get_procedure_steps():
    global current_step, procedure_steps

    # The index for the current step. We are always starting with the first step (0 in an array)
    current_step = 1

    # Getting the steps for the selected procedure from the Database
    procedure_steps = requests.get(DB_ADDR + "/proceduresteps/" +
                                   str(selected_procedure)).json()

    # Getting the instructions for the first step
    first_step = procedure_steps["steps"][current_step - 1]["description"]

    # create dialogue output for VUI
    output_message = "Let's start! When you are ready for the next step, please say next! Here is the first step. {} ".format(
        first_step)

    return output_message

# auxiliary function to get the output messages for each STAGE and STATE
def get_repeat_message_output():
    global STAGE, STATE, procedures_list, selected_procedure_title, resources_list, current_step, procedure_steps
    output_message = "I don't remember what I just said either... Sorry..."

    # get the message for the stage and state
    if STAGE == 0 and STATE == 0:
        print("Repeating message for: STATE 0.0")
        output_message = "Ask me for help, and I will tell you what you can do!"

    if STAGE == 1 and STATE == 1:
        print("Repeating message for: STATE 1.1")
        output_message = "Okay! Please select an experiment, and tell me its number. {}".format(
            procedures_list)

    if STAGE == 2 and STATE == 1:
        print("Repeating message for: STATE 2.1")
        output_message = "Here is what you will need for the experiment, {}. {}. To go on, please call me and say, start experiment.".format(
            selected_procedure_title, resources_list)

    if STAGE == 3 and STATE == 1:
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]
        print("Repeating message for: STATE 3.1")
        output_message = "Alright! Let me know when you are ready for the next step. Here is the first step: {}".format(
            step_description)

    if STAGE == 3 and STATE == 2:
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]
        print("Repeating message for: STATE 3.2")
        output_message = "Okay! {}".format(step_description)

    if STAGE == 3 and STATE == 3:
        step_description = procedure_steps["steps"][current_step -
                                                    1]["description"]
        print("Repeating message for: STATE 3.3")
        output_message = "Alright! Please tell me when you are done. The last step is. {}".format(
            step_description)

    return output_message

# auxiliary function to get the manual messages for each STAGE and STATE
def get_manual_message_output():
    global STAGE, STATE, total_steps, current_step

    output_message = "I am lost and I do not know what the hell we are doing either..."

    # get the message for the stage and state
    if STAGE == 0 and STATE == 0:
        print("Getting the manual for: STATE 0.0")
        output_message = "Hi! Let me show you how I can help you. After I finishe talking, you can call me by saying, hey Snips, and ask me to repeat or ask me to stop. Right now, you can call me, and say you want to start an experiment!"

    if STAGE == 1 and STATE == 1:
        print("Getting the manual for: STATE 1.1")
        output_message = "We are selecting an experiment to start. After I finishe talking, you can ask me to, select an experiment, repeat the message, or stop the conversation. To select an experiment, tell me its number!"

    if STAGE == 2 and STATE == 1:
        print("Getting the manual for: STATE 2.1")
        output_message = "Right now, I'm telling you the resources you need for this experiment. After I finishe talking, you can ask me to, start the experiment, repeat the message, or to stop."

    if STAGE == 3 and STATE == 1:
        print("Getting the manual for: STATE 3.1")
        output_message = "We are currently at, the first step, of this experiment. You can ask me to continue to the next step, to repeat the message, or to stop the experiment."

    if STAGE == 3 and STATE == 2:
        print("Getting the manual for: STATE 3.2")
        output_message = "We are currently at, step, {}. You can ask me to, repeat the message, or to stop the experiment. You can also call me, and ask me to go to the previous step, or the next step.".format(
            current_step)

    if STAGE == 3 and STATE == 3:
        print("Getting the manual for: STATE 3.3")
        output_message = "We are currently at, the last step. You can ask me to, repeat the message. You can also call me, and ask me to go to the previous step, or to finishe the experiment!"

    return output_message

# get the short message of contextualisation for when the wrong intent is recognised
def get_wrong_intent_message():
    global STAGE, STATE, selected_procedure, procedures, total_steps, current_step

    if STAGE == 0 and STATE == 0:
        print("WRONG INTENT RECOGNIZED, STATE 0.0")
        output_message = "I didn't get that. Right now, you can call me by saying, hey Snips, I want to start an experiment!"

    if STAGE == 1 and STATE == 1:
        print("WRONG INTENT RECOGNIZED, STATE 1.1")
        output_message = "I didn't get that. Please call me, and select a number from one to six."

    if STAGE == 1 and STATE == 2:
        print("WRONG INTENT RECOGNIZED, STATE 1.2")
        output_message = "I didn't get that. You selected {}, {}. Is this correct?".format(
            str(selected_procedure),
            str(procedures[selected_procedure - 1]["title"]))

    if STAGE == 2 and STATE == 1:
        print("WRONG INTENT RECOGNIZED, STATE 2.1")
        output_message = "I didn't get that. Right now, you can call me, and let me know when you are ready to start the experiment!".format(
            selected_procedure_title)

    if STAGE == 3 and STATE == 1:
        print("WRONG INTENT RECOGNIZED, STATE 3.1")
        output_message = "I didn't get that. Please call me again, and let me know when you want to continue to the next step.".format(
            selected_procedure_title)

    if STAGE == 3 and STATE == 2:
        print("WRONG INTENT RECOGNIZED, STATE 3.2")
        output_message = "I didn't get that. You can call me, and ask me to go to the previous step, or the next step.".format(
            current_step)

    if STAGE == 3 and STATE == 3:
        print("WRONG INTENT RECOGNIZED, STATE 3.3")
        output_message = "I didn't get that. Please call me again, and ask me to go to the previous step, or to finishe the experiment!".format(
            current_step)

    return output_message

# method executed when there is an unrecognized intent
def unrecognizedIntentHandler(hermes, intent_message):
    global STAGE, STATE, selected_procedure, procedures, total_steps, current_step

    if STAGE == 0 and STATE == 0:
        print("INTENT NOT RECOGNIZED, STATE 0.0")
        output_message = "Sorry, I didn't understand that. Right now, you can call me, by saying, hey Cassy, and say you want to start an experiment!"

    if STAGE == 1 and STATE == 1:
        print("INTENT NOT RECOGNIZED, STATE 1.1")
        output_message = "Sorry, I didn't get it. Please call me, and, select a number from one to six"

    if STAGE == 1 and STATE == 2:
        print("INTENT NOT RECOGNIZED, STATE 1.1")
        output_message = "Sorry, I didn't understand that. You selected {}, {}. Is this correct?".format(
            str(selected_procedure),
            str(procedures[selected_procedure - 1]["title"]))
        return hermes.publish_continue_session(intent_message.session_id, output_message, [INTENT_CONFIRM, INTENT_CANCEL])

    if STAGE == 2 and STATE == 1:
        print("INTENT NOT RECOGNIZED, STATE 2.1")
        output_message = "Sorry, I didn't understand that. Right now, you can call me, and let me know when you are ready to start the experiment!".format(
            selected_procedure_title)

    if STAGE == 3 and STATE == 1:
        print("INTENT NOT RECOGNIZED, STATE 3.1")
        output_message = "I don't understand what you just said, sorry. Please call me again, and let me know when you want to continue to the next step.".format(
            selected_procedure_title)

    if STAGE == 3 and STATE == 2:
        print("INTENT NOT RECOGNIZED, STATE 3.2")
        output_message = "Sorry, I didn't get it. You can call me, and ask me to go to the previous step, or, the next step, if you want to.".format(
            current_step)

    if STAGE == 3 and STATE == 3:
        print("INTENT NOT RECOGNIZED, STATE 3.3")
        output_message = "I didn't understand what you're saying. Please call me again, and ask me to go to the previous step, or, finish the experiment!".format(
            current_step)

    return hermes.publish_end_session(intent_message.session_id,
                                      output_message)

# returns True if HDMI is connected
def isConnected():
    #cmd = ['sudo', 'tvservice', '-s']
    #proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #o, e = proc.communicate()
    # return re.search("^state 0x.*a$", o.decode('ascii'))
    return True


def send(str):
    ws = create_connection("ws://mighty-eyrie-55026.herokuapp.com")
    ws.send(str)
    print("Sent")
    print("Recieving...")
    ws.close()

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedures) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_START, start_procedure) \
        .subscribe_intent(INTENT_NEXT, next_step) \
        .subscribe_intent(INTENT_PREVIOUS, previous_step) \
        .subscribe_intent(INTENT_FINISH, finish_procedure) \
        .subscribe_intent(INTENT_REPEAT, repeat) \
        .subscribe_intent(INTENT_HELP, help_intent) \
        .subscribe_intent(INTENT_CONFIRM_CANCEL, confirm_cancel) \
        .subscribe_intent(INTENT_HELLO, hello) \
        .start()
