sensor = get_component("pressure_sensor")
value = sensor.get_value()

sensor.stabilize(value + value % 2)