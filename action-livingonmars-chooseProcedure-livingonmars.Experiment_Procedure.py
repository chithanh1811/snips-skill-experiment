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
INTENT_SHOW = "livingonmars:showProcedure"

def choose_procedure(hermes, intent_message):
    with open('sample-response') as database_response:
        procedures = json.load(database_response)

    print("The user is choosing an experiment")
    raw_choice = intent_message["slots"][0]["rawValue"]
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

    sentence = "You chose" + choice + " " + procedures[choice - 1] + ". Is that correct?"
    hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CONFIRM, INTENT_CANCEL])

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_CHOOSE, choose_procedure).start()
