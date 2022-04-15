from typing import Tuple
import pymongo
import json
import smtplib
import os
import secrets

from jsonschema import validate, ValidationError

LOGIN_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "token": {
            "type": "string"
        },
        "id": {
            "type": "string"
        }
    }   
}

REGISTER_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "email": {
            "type": "string"
        }
    }   
}

class AuthHandler:
    def __init__(self, db_connect: Tuple[str, int], smtp_login_pass: Tuple[str, int]):
        self.__db_server, self.__db_port = db_connect

        self.__server_email = smtplib.SMTP('smtp.yandex.ru', 587)
        self.__server_email.ehlo() 
        self.__server_email.starttls()
        self.__server_email.login(smtp_login_pass[0], smtp_login_pass[1])
        self.__email = smtp_login_pass[0]

        # TODO Add database
        # self.__user_db = 
    
    def register(self, user_data: dict) -> bool:
        ok = True
        try:
            validate(instance=user_data, schema=REGISTER_SCHEME)
            # TODO: Add field in database
        except ValidationError:
            ok = False
        
        if ok:
            gen_token = secrets.token_hex(16)
            try:
                dest_email = user_data['email']
                subject = 'HDULab'
                email_text = 'Registration complete\n Your HDU Key: ' + gen_token
                message = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (self.__email, dest_email, subject, email_text)
                # self.__server_email.set_debuglevel(1) # Необязательно; так будут отображаться данные с сервера в консоли
                # self.__server_email.sendmail(self.__email, dest_email, message)
            except:
                ok = False
        return ok

    
    def auth(self, user_data: dict) -> bool:
        try:
            validate(instance=user_data, schema=LOGIN_SCHEME)
            # TODO: Add field in database
            return True
        except ValidationError:
            return False
        # db_key =
        # if db_key == user_data
