thermometer = get_component("thermometer")
transmitter = get_component("transmitter")


current_temperature = thermometer.get_value()

transmitter.connect("earth")
transmitter.transmit("current_temperature", current_temperature)