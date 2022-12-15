import simpleModbus as modbus 

if __name__ == '__main__':
    # Connectivity variables
    host = 'localhost'
    port = 502
    unit1 = 1
    unit2 = 2

    # Modbus server startup
    print('\nModbus server startup')
    server = modbus.ModbusServer(host, port)
    server.daemon = False

    # Memory map slave 1 startup
    print('\nCreating memory map for slave 1')
    server.setup_memory_map(
        unit=unit1,
        hr_count=4,
        ir_count=4,
    )

    # Memory map slave 2 startup
    print('Creating memory map for slave 2') 
    server.setup_memory_map(
        unit=unit2,
        hr_count=12,
        ir_count=12,
    )

    # Run modbus server
    print('\nStarting modbus server ...')
    server.start_server()

    # Modify memory map slave 2
    print('\nModifying memory map for slave 2')
    server.remove_memory_map(unit2)
    server.setup_memory_map(
        unit=unit2,
        hr_count=8,
        ir_count=8,
    )

    # Stop modbus server
    print('\nStopping modbus server ...\n')
    server.stop()

    # Clone server for run again 
    print('\nCloning server for run again')
    server = server.clone()

    # Run modbus server
    print('\nStarting modbus server ...')
    server.start_server()

    # Write input registers slave 1
    print('\nWriting input registers slave 1')
    i_registers1 = {30001: 1, 30002: 2}
    server.write_input_registers(i_registers1, unit1)

    # Write holding registers slave 1
    print('Writing holding registers slave 1')
    w_registers1 = {40001: 1, 40002: 2}
    server.write_holding_registers(w_registers1, unit1)

    # Write input registers slave 2
    print('\nWriting input registers slave 2')
    i_registers2 = {30001: 10, 30002: 20}
    server.write_input_registers(i_registers2, unit2)

    # Write holding registers slave 2
    print('Writing holding registers slave 2')
    w_registers2 = {40100: 10, 40101: 20}
    server.write_holding_registers(w_registers2, unit2)

    # Client modbus startup
    print('\nClient modbus startup')
    client = modbus.ModbusClient(host, port)
    client.connect()

    # Read registers for slave 1 
    print('\nReading registers for slave 1')
    client.unit = unit1
    print(client.read_input_registers(address=30001, count=4))
    print(client.read_holding_registers(address=40001, count=4))
    
    # Read registers for slave 2
    print('\nReading registers for slave 2')
    client.unit = unit2
    print(client.read_input_registers(address=30001, count=8))
    print(client.read_holding_registers(address=40100, count=8))

    print('\nClient writes holding registers 40102 and 40103 for slave 2')
    client.write_holding_registers({40102: 30, 40103: 40})
    
    print('\nReading holding registers for slave 2:')
    print(client.read_holding_registers(address=40100, count=8))

    # Stop client and server modbus
    print('\nStopping modbus client ...')
    client.stop()
    print('Stopping modbus server ...')
    server.stop()
