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

def randomize_procedure(hermes, intent_message):
    with open('sample-response') as database_response:
        procedures = json.load(database_response)

    print("The user is asking to start a random experiment")

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_RANDOM, randomize_procedure).start()
