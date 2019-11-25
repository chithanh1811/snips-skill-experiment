#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from hermes_python.ontology import *
import io

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

class SnipsConfigParser(configparser.SafeConfigParser):
    def to_dict(self):
        return {section : {option_name : option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, configparser.Error) as e:
        return dict()

def subscribe_intent_callback(hermes, intentMessage):
    conf = read_configuration_file(CONFIG_INI)
    action_wrapper(hermes, intentMessage, conf)


def action_wrapper(hermes, intentMessage, conf):
    """ Write the body of the function that will be executed once the intent is recognized. 
    In your scope, you have the following objects : 
    - intentMessage : an object that represents the recognized intent
    - hermes : an object with methods to communicate with the MQTT bus following the hermes protocol. 
    - conf : a dictionary that holds the skills parameters you defined. 
      To access global parameters use conf['global']['parameterName']. For end-user parameters use conf['secret']['parameterName'] 
     
    Refer to the documentation for further details. 
    """ 
    MQTT_IP_ADDR = "localhost"
    MQTT_PORT = 1883
    MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))
    
    INTENT_CANCEL = "cancelProcedure"
    INTENT_CONFIRM = "confirmProcedure"
    INTENT_CHOOSE = "chooseProcedure"
    INTENT_RANDOM = "randomizeProcedure"
    INTENT_SHOW = "showProcedure"
    
    def show_procedure(hermes, intent_message):
        print("The user is asking to show the experiment list")
    
        with open('sample-response') as database_response:
            procedures = json.load(database_response)
    
        order_number = 0
        sentence = None
        for procedure in procedures:
            order_number += 1
            sentence += "Select " + order_number + "for the experiment " + procedure["title"] + ". "
    
        hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_RANDOM, INTENT_CANCEL, INTENT_CHOOSE])
    
    with Hermes(MQTT_ADDR) as h:
        h.subscribe_intent(INTENT_SHOW, show_procedure)
    


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("livingonmars:showProcedures", subscribe_intent_callback) \
         .start()
