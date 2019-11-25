#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hermes_python.hermes import Hermes
import requests
import json
import random

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_CANCEL = "livingonmars:cancelProcedure"
INTENT_CONFIRM = "livingonmars:confirmProcedure"
INTENT_CHOOSE = "livingonmars:chooseProcedure"
INTENT_RANDOM = "livingonmars:randomizeProcedure"
INTENT_SHOW = "livingonmars:showProcedures"
    
with open('sample-response.json') as database_response:
    procedures = json.load(database_response)

def show_procedure(hermes, intent_message):
    print("The user is asking to show the experiment list")

    order_number = 0
    sentence = "Select"
    for procedure in procedures:
        order_number += 1
        sentence += str(order_number) + ". " + procedure["title"] + ". "

    return hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CANCEL, INTENT_CHOOSE])

def randomize_procedure(hermes, intent_message):
    print("The user is asking to start a random experiment")
    return hermes.publish_continue_session(intent_message.session_id, "randomize", [INTENT_CONFIRM])

def cancel_procedure(hermes, intent_message):
    sentence = "You cancelled the request"
    return hermes.publish_end_session(intent_message.session_id, sentence)

def choose_procedure(hermes, intent_message):
    print("The user is choosing an experiment")
    raw_choice = intent_message.slots.procedure.first().value
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
        choice = raw_choice

    sentence = "You chose " + str(choice) + ". " + str(procedures[choice-1]["title"]) + ". Is that correct?"
    return hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CONFIRM, INTENT_CANCEL])

def confirm_procedure(hermes, intent_message):
    print("The user is confirming to start an experiment")
    raw_choice = intent_message.slots.confirmation.first().value
    if raw_choice == "yes":
        sentence = "Experiment started"
        return hermes.publish_end_session(intent_message.session_id, sentence)
    else:
        sentence = "Which experiment do you want to start?"
        return hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CHOOSE, INTENT_RANDOM, INTENT_CANCEL])

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedure) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_RANDOM, randomize_procedure) \
        .start()
