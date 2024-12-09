import os
import pandas as pd
from pyaedt import Q3d, Edb

# Constants
AEDT_VERSION = "2024.2"
NUM_CORES = 4
NG_MODE = False

# User inputs
project_folder = input("Enter project folder path: ")
edb_file = input("Enter EDB file path: ")
csv_file = input("Enter CSV file path for harmonic current data: ")
hs_switch = input("Enter high-side switch designator: ")
ls_switch = input("Enter low-side switch designator: ")
net_vin = input("Enter net name for Vin: ")
net_gnd = input("Enter net name for ground: ")
net_sw = input("Enter net name for switch node: ")

# Load harmonic data
harmonic_data = pd.read_csv(csv_file)
print("Harmonic data loaded successfully.")

# Open EDB project
edb = Edb(edb_file, edbversion=AEDT_VERSION)
print(f"Opened EDB file: {edb_file}")

# Identify pins
def find_pin(component, net_name):
    return [
        pin for pin in edb.components[component].pins.values()
        if pin.net_name == net_name
    ][0]

hs_pin = find_pin(hs_switch, net_sw)
ls_pin = find_pin(ls_switch, net_sw)
vin_pin = find_pin(hs_switch, net_vin)
gnd_pin = find_pin(hs_switch, net_gnd)

print(f"HS Switch Pin: {hs_pin.position}")
print(f"LS Switch Pin: {ls_pin.position}")
print(f"Vin Pin: {vin_pin.position}")
print(f"GND Pin: {gnd_pin.position}")

# Close EDB after pin identification
edb.save_edb()
edb.close_edb()

# Open Q3D
q3d_project_path = os.path.join(project_folder, "Exported_Q3D.aedt")
q3d = Q3d(q3d_project_path, version=AEDT_VERSION)
print("Q3D project loaded successfully.")

# Results container
results = []

# Iterate over frequencies
for _, row in harmonic_data.iterrows():
    freq = row["Frequency"]
    hs_current = row["High Side Current"]
    ls_current = row["Low Side Current"]

    print(f"Running analysis for frequency: {freq} Hz")

    # Set source currents
    q3d.create_source(hs_pin.position, net_name=net_vin, current=f"{hs_current}A")
    q3d.create_sink(ls_pin.position, net_name=net_gnd, current=f"{ls_current}A")

    # Update frequency and analyze
    setup = q3d.create_setup()
    setup.props["SaveFields"] = True
    setup.analyze()

    # Extract temperatures at pin positions
    hs_temp = q3d.post.get_value_at_location(hs_pin.position, "Temperature", setup.name)
    ls_temp = q3d.post.get_value_at_location(ls_pin.position, "Temperature", setup.name)

    results.append({
        "Frequency (Hz)": freq,
        "HS Temp (C)": hs_temp,
        "LS Temp (C)": ls_temp,
    })

# Save results to CSV
output_csv = os.path.join(project_folder, "DCIR_Temperature_Results.csv")
pd.DataFrame(results).to_csv(output_csv, index=False)
print(f"Results saved to: {output_csv}")

# Release Q3D
q3d.release_desktop()
print("Q3D analysis complete and desktop released.")
