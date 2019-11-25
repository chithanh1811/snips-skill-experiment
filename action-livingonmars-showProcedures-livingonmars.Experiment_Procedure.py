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
    
def show_procedure(hermes, intent_message):
    print("The user is asking to show the experiment list")

    with open('sample-response.json') as database_response:
        procedures = json.load(database_response)

    order_number = 0
    sentence = None
    for procedure in procedures:
        order_number += 1
        sentence += "Select " + str(order_number) + "for the experiment " + procedure["title"] + ". "

    hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_RANDOM, INTENT_CANCEL, INTENT_CHOOSE])

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedure).start()
