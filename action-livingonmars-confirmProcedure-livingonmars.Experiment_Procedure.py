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

def confirm_procedure(hermes, intent_message):
    with open('sample-response') as database_response:
        procedures = json.load(database_response)

    print("The user is confirming to start an experiment")
    raw_choice = intent_message["slots"][0]["value"]["value"]
    if raw_choice == "yes":
        sentence = "Experiment started"
        hermes.publish_end_session(intent_message.session_id, sentence)
    else:
        sentence = "Which experiment do you want to start?"
        hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CHOOSE, INTENT_RANDOM, INTENT_CANCEL])

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_CONFIRM, confirm_procedure).start()
