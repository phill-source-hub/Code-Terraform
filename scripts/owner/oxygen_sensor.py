sensor = get_component("oxygen_sensor")
raw_value = sensor.get_value()

fixed_value = round(raw_value * 100, 6)

sensor.calibrate(fixed_value)