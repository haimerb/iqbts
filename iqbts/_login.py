from iqoptionapi.stable_api import IQ_Option
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')

class Login:
   Iq=None
   def __init__(self):
    Iq=IQ_Option("hbarbetti.ing@gmail.com","DeporvidaCdc1*")

    def do_login():
        check, reason=Iq.connect()
        print(check, reason)        
    do_login()

    def is_connected():
        return self.connected
    is_connected()

