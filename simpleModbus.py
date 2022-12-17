import pymodbus

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder, Endian 
from pymodbus import exceptions, pdu 

from pymodbus.server import StartTcpServer, ServerStop
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

import threading 
import time


class ModbusBase:

    @property
    def host(self):
        return self.__host

    
    @host.setter
    def host(self, host_ : str):
        self.__host = host_


    @property
    def port(self):
        return self.__port
        

    @port.setter
    def port(self, port_ : int):
        if port_>= 0 and port_ <= 65536:
            self.__port = port_
        else:
            raise ValueError('Modbus port out of range. Valid range 0 to 65536')
             

    def get_pdu_exception_cause(self, response):
        if isinstance(response, pdu.ExceptionResponse):
            response = str(response)

            try:
                i = response.index('(')
                try:
                    e = response.index(')')
                    response = list(response[i+1:e].split(','))
                    if len(response) > 2:
                        response = response[2].replace(' ', '') 
                except ValueError:
                    pass
            except ValueError:
                pass

            return response


    def encode_value_to_integer(self, value : int):
        if value < -32768 or value > 32767:
            raise ValueError(f'Value {value} cannot be encoded with 16 bits. Range -32768 to 32767')

        builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
        builder.reset()
        builder.add_16bit_int(value)
        binary = builder.to_registers()[0]

        return binary


    def decode_binary_registers_to_integer(self, response):
        decoder = BinaryPayloadDecoder.fromRegisters(registers=response.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        out = []
        try:
            while True:
                out.append(decoder.decode_16bit_int())
        except:
            pass

        return out


class ModbusClient(ModbusBase):

    def __init__(self, host : str, port : int, unit : int = 1):
        self.host = host
        self.port = port
        self.unit = unit
        self.__client = None


    @property
    def unit(self):
        return self.__unit


    @unit.setter
    def unit(self, unit_ : int):
        if unit_ >= 0 and unit_ <= 255:
            self.__unit = unit_
        else:
            raise ValueError('Modbus unit of range. Valid range 0 to 255')


    def connect(self):
        if self.host and self.port:
            self.__client = ModbusTcpClient(host=self.host, port=self.port)
            self.stop()
            status = self.__client.connect() 

            if not status:
                raise exceptions.ModbusException(f'Failed to connect to {self.host}:{self.port} modbus server')
        else:
            raise ValueError('Error connecting to modbus server. No set host or/and port')


    def is_connected(self):
        if self.__client:
            return self.__client.is_socket_open()
        else:
            return False


    def stop(self):
        try:
            self.__client.close()
        except BaseException:
            raise exceptions.ModbusException('Client not started. Execute connect() function previously')


    def quit(self):
        self.stop()


    def read_input_registers(self, address : int = 30001, count : int = 1) -> dict:
        if not self.unit:
            raise ValueError('Not defined server unit (slave id)')

        if not (address > 30000 and address < 40000):
            raise ValueError('Input register address is out of range. Valid range 30001 to 365536')

        if not (count > 0 and count <= 125):
            raise ValueError('Number of input registers is out of range. Count valid range 1 to 125')

        if not (count > 0 and (address + count) < 40000):
            raise ValueError('Number of input registers is out of range. Address plus count value is greater than 65536') 

        if not self.__client:
            raise exceptions.ModbusException('Client not started. Execute connect() function previously')

        response = self.__client.read_input_registers(address-30001, count, slave=self.unit)
        
        if isinstance(response, pdu.ExceptionResponse):
            response = self.get_pdu_exception_cause(response)
            raise exceptions.ModbusException('Received response error. '+response)

        if isinstance(response, pymodbus.register_read_message.ReadInputRegistersResponse):
            input_registers = self.decode_binary_registers_to_integer(response=response)
        else:
            input_registers = []

        dict_input_registers = {}
        for input_register in input_registers:
            dict_input_registers[str(address)] = input_register
            address += 1

        return dict_input_registers


    def read_holding_registers(self, address : int = 40001, count : int = 1) -> dict:
        if not self.unit:
            raise ValueError('Not defined server unit (slave id)')

        if not (address > 40000 and address < 50000):
            raise ValueError('Holding register address is out of range. Valid range 40001 to 465536')
        
        if not (count > 0 and count <= 125):
            raise ValueError('Number of holding registers is out of range. Count valid range 1 to 125')

        if not (count > 0 and (address + count) < 50000):
            raise ValueError('Number of holding registers is out of range. Address plus count value is greater than 65536') 
        
        if not self.__client:
            raise exceptions.ModbusException('Client not started. Execute connect() function previously')

        response = self.__client.read_holding_registers(address-40001, count, slave=self.unit)
        
        if isinstance(response, pdu.ExceptionResponse):
            response = self.get_pdu_exception_cause(response)
            raise exceptions.ModbusException('Received response error. '+response)

        if isinstance(response, pymodbus.register_read_message.ReadHoldingRegistersResponse):
            holding_registers = self.decode_binary_registers_to_integer(response=response)
        else:
            holding_registers = []

        dict_holding_registers = {}
        for holding_register in holding_registers:
            dict_holding_registers[str(address)] = holding_register
            address += 1

        return dict_holding_registers
        

    def write_holding_registers(self, holding_registers : dict):
        """
            Write holding registers on server (host, port, unit).

            Args:

                holding_register (dict): Holding registers to write on server
                {
                    [address : int]: value : int,
                    [40001]: 245,
                    ...
                }
        """
        if not self.unit:
            raise ValueError('Not defined server unit (slave id)')

        if not self.__client:
            raise ValueError('Client not started. Execute connect() function previously')

        for address in holding_registers:
            if address > 40000 and address < 50000:
                modbus_value = self.encode_value_to_integer(holding_registers[address])

                # Writting holding register
                self.__client.write_register(address-40001, modbus_value, unit=self.unit)
            else:
                raise ValueError(f'Modbus address {address} out of range. Holding registers range 40001 to 49999')
    

class ModbusServer(threading.Thread, ModbusBase):
    
    def __init__(self, host : str, port : int):
        """
            Modbus server constructor. 

            Args:

                host (str): IP address or URL server deployment. To use any interface use ""
                port (int): Port to server deployment
        """
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.__server_memory = {}
        self.__context = None
        self.__holding_registers_count = {}
        self.__input_registers_count = {}
        self.__exit = threading.Event()


    def get_holding_registers_count(self, unit : int):
        try:
            return self.__holding_registers_count[unit]
        except KeyError:
            return 0


    def get_input_registers_count(self, unit : int):
        try:
            return self.__input_registers_count[unit]
        except KeyError:
            return 0


    def start_server(self, number_attempts : int = 4):
        self.start()
        while not self.is_started() and number_attempts > 0: 
            number_attempts -= 1
            time.sleep(0.5)

        if number_attempts <= 0:
            raise exceptions.ModbusException('Server start failure')


    def is_running(self):
        return not self.__exit.is_set()


    def stop(self):
        self.__exit.set()
        try:
            ServerStop()

            while self.is_started():
                time.sleep(0.5)
        except IndexError:
            raise exceptions.ModbusException('Server stop failure')


    def quit(self):
        self.stop()


    def is_started(self):
        try:
            client = ModbusClient(self.host, self.port)

            client.connect()
            client.stop()
            del client

            return True
        except AssertionError:
            return False
        except exceptions.ModbusException:
            return False


    def clone(self):
        server = ModbusServer(self.host, self.port)
        server.daemon = self.daemon
        
        registers = {}
        for unit in self.__input_registers_count:
            registers[unit] = {'ir': self.__input_registers_count[unit]}

        for unit in self.__holding_registers_count:
            registers[unit] = {'hr': self.__holding_registers_count[unit]}

        for unit in registers:
            try:
                ir_count = registers[unit]['ir']
            except KeyError:
                ir_count = 0
            try:
                hr_count = registers[unit]['hr']
            except KeyError:
                hr_count = 0

            server.setup_memory_map(unit, ir_count, hr_count)

        return server


    def remove_memory_map(self, unit : int):
        """
            Remove memory map to unit slave and stop the server. The changes will be reflected after restarting the server
        """
        try:
            del self.__server_memory[unit]
        except KeyError:
            pass


    def setup_memory_map(self, unit : int, ir_count : int = 0, hr_count : int = 0):
        """
            Setup memory map to modbus server

            Args:
                unit (int): Slave modbus identifier
                ir_count (int): Input registers counts
                hr_count (int): Holding registers counts
        """
        for u in self.__server_memory:
            if u == unit:
                raise ValueError(f'Server identifier {unit} is already in use. Remove it first using remove_memory_map() function')
        
        kwargs = {}

        if ir_count < 0:
            raise ValueError('Invalid input registers counts. Valid range between 1 and 10000')
        elif ir_count == 0:
            pass
        else:
            ir_memory = ModbusSequentialDataBlock(address=0, values=[0,]*ir_count)
            kwargs['ir'] = ir_memory
            self.__input_registers_count[unit] = ir_count

        if hr_count < 0:
            raise ValueError('Invalid holding registers count. Valid range between 1 and 10000')
        elif hr_count == 0:
            pass
        else:
            hr_memory = ModbusSequentialDataBlock(address=0, values=[0,]*hr_count)
            kwargs['hr'] = hr_memory 
            self.__holding_registers_count[unit] = hr_count

        kwargs['zero_mode'] = True
        kwargs['unit'] = unit

        self.__server_memory[unit] = ModbusSlaveContext(kwargs=kwargs)
        

    def write_input_registers(self, input_registers : dict, unit : int = 1):
        """
            Write input registers on server 

            Args:

                input_registers (dict): Input registers to write on server
                {
                    [address : int]: value : int,
                    [30001]: 245,
                    ...
                }
                unit (int): Slave modbus identifier. Default value 1
        """   
        if unit < 0 or unit > 255:
            raise ValueError('Modbus identifier out of range. Range 0 to 255') 

        if isinstance(self.__context, type(None)):
            raise exceptions.ModbusException('Server has not been started. Start it using the start() function')

        if len(self.__server_memory) == 0:
            raise ValueError('There are no memory maps on the modbus server. Create a memory map with the setup_memory_map() function')

        for address in input_registers:
            if address > 30000 and address < 40000:
                modbus_value = self.encode_value_to_integer(input_registers[address])

                # Writting input register
                self.__context[unit].setValues(4, address-30001, [modbus_value,])
            else:
                raise ValueError(f'Modbus address {address} out of range. Input registers range 30001 to 39999')


    def write_holding_registers(self, holding_registers : dict, unit : int = 1):
        """
            Write holding registers on server 

            Args:

                holding_registers (dict): Holding registers to write on server
                {
                    [address : int]: value : int,
                    [40001]: 245,
                    ...
                }
                unit (int): Slave modbus identifier. Default value 1
        """   
        if unit < 0 or unit > 255:
            raise ValueError('Modbus identifier out of range. Range 0 to 255') 

        if isinstance(self.__context, type(None)):
            raise exceptions.ModbusException('Server has not been started. Start it using the start() function')

        if len(self.__server_memory) == 0:
            raise ValueError('There are no memory maps on the modbus server. Create a memory map with the setup_memory_map() function')
        
        for address in holding_registers:
            if address > 40000 and address < 50000:
                modbus_value = self.encode_value_to_integer(holding_registers[address])

                # Writting holding register
                self.__context[unit].setValues(6, address-40001, [modbus_value,])
            else:
                raise ValueError(f'Modbus address {address} out of range. Holding registers range 40001 to 49999')
    

    def run(self):
        if len(self.__server_memory) == 0:
            raise ValueError('Error starting modbus server. Its memory map has not been defined. Use setup_memory_map() function')
            
        while self.is_running():
            try:
                self.__context = ModbusServerContext(slaves=self.__server_memory, single=False)
                StartTcpServer(
                    context=self.__context, 
                    address=(self.host, self.port),
                    defer_start=False
                )
            except KeyboardInterrupt:
                break
            except BaseException as be:
                del self.__context
                print(f'Server modbus exception. {be}')
                time.sleep(2)

        print('Modbus server stopped')
        self.__exit.clear()