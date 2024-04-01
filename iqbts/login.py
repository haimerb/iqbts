from iqoptionapi.stable_api import IQ_Option
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')
Iq=IQ_Option("hbarbetti.ing@gmail.com","DeporvidaCdc1*")
check, reason=Iq.connect()#connect to iqoption
print(check, reason)
###print('CONECTADO? '+Iq.check_connect())
connected=Iq.check_connect()
print('CONECTADO? ', 'SI' if connected==True else 'NO')