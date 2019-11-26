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

DB_ADDR = "http://localhost:8000"
GUI_ADDR = "http://localhost:4000"

procedures = requests.get(DB_ADDR + "/procedures").json()

def show_procedure(hermes, intent_message):
    print("The user is asking to show the experiment list")

    order_number = 0
    sentence = ""
    for procedure in procedures:
        order_number += 1
        sentence += str(order_number) + ". " + procedure["title"] + ". "

    r = requests.post(GUI_ADDR + "/show", json = procedures)

    return hermes.publish_continue_session(intent_message.session_id, "Which experiment do you want to start", [INTENT_CANCEL, INTENT_CHOOSE])

def randomize_procedure(hermes, intent_message):
    print("The user is asking to start a random experiment")
    return hermes.publish_continue_session(intent_message.session_id, "randomize", [INTENT_CONFIRM])

def cancel_procedure(hermes, intent_message):
    print("The user is asking to cancel the request")
    r = requests.post(GUI_ADDR + "/cancel", json = {'cancel': 'true'})
    return hermes.publish_end_session(intent_message.session_id, "You cancelled the request")

def choose_procedure(hermes, intent_message):
    print("The user is choosing an experiment")
    raw_choice = intent_message.slots.procedure.first().value
    if raw_choice == "one":
        choice = 1
        r = requests.post(GUI_ADDR + "/select", json = {'id': '1'})
    elif raw_choice == "two":
        choice = 2
        r = requests.post(GUI_ADDR + "/select", json = {'id': '2'})
    elif raw_choice == "three":
        choice = 3
        r = requests.post(GUI_ADDR + "/select", json = {'id': '3'})
    elif raw_choice == "four":
        choice = 4
        r = requests.post(GUI_ADDR + "/select", json = {'id': '4'})
    elif raw_choice == "five":
        choice = 5
        r = requests.post(GUI_ADDR + "/select", json = {'id': '5'})
    elif raw_choice == "six":
        choice = 6
        r = requests.post(GUI_ADDR + "/select", json = {'id': '6'})
    else:
    	return hermes.publish_continue_session(intent_message.session_id, "Please select a number!", [INTENT_CHOOSE])

    sentence = "You selected " + str(choice) + ". " + str(procedures[choice-1]["title"]) + ". Is that correct?"
    return hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CONFIRM, INTENT_CANCEL])

def confirm_procedure(hermes, intent_message):
    print("The user is confirming to start an experiment")
    raw_choice = intent_message.slots.confirmation.first().value
    if raw_choice == "yes":
        sentence = "Experiment started"
        r = requests.post(GUI_ADDR + "/confirm", json = {'confirm': 'true'})
        return hermes.publish_end_session(intent_message.session_id, sentence)
    else:
        sentence = "Which experiment do you want to start?"
        r = requests.post(GUI_ADDR + "/show", json = procedures)
        return hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_CHOOSE, INTENT_RANDOM, INTENT_CANCEL])

with Hermes(MQTT_ADDR) as h:
    h.subscribe_intent(INTENT_SHOW, show_procedure) \
        .subscribe_intent(INTENT_CONFIRM, confirm_procedure) \
        .subscribe_intent(INTENT_CANCEL, cancel_procedure) \
        .subscribe_intent(INTENT_CHOOSE, choose_procedure) \
        .subscribe_intent(INTENT_RANDOM, randomize_procedure) \
        .start()
