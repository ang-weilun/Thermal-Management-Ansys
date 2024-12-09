import os
import csv
from ansys.aedt.core import Icepak

def setup_solve_and_export_results(
    project_folder, idf_file, bdf_file, edb_file, device_losses, output_csv, aedt_version="2024.2", ng_mode=False
):
    """
    Sets up an IcePak simulation, assigns power losses to devices, solves the simulation, and exports results.

    Parameters:
    - project_folder (str): Directory where the project will be saved.
    - idf_file (str): Path to the IDF file.
    - bdf_file (str): Path to the BDF file.
    - edb_file (str): Path to the EDB file.
    - device_losses (dict): Dictionary of device designators and their power losses.
                            Example: {"Q1": "5W", "D1": "3W"}
    - output_csv (str): Path to the output CSV file.
    - aedt_version (str): AEDT version to use. Default is "2024.2".
    - ng_mode (bool): Non-graphical mode. Default is False.
    """
    # Ensure the project folder exists
    if not os.path.exists(project_folder):
        os.makedirs(project_folder)

    # Define the project path
    project_path = os.path.join(project_folder, "Icepak_Project.aedt")

    # Launch IcePak
    ipk = Icepak(
        project=project_path,
        version=aedt_version,
        new_desktop=True,
        non_graphical=ng_mode,
    )

    try:
        # Import IDF and BDF files
        print("Importing IDF and BDF files...")
        ipk.import_idf(board_path=bdf_file)

        # Save the project after IDF import
        ipk.save_project()

        # Import the EDB file using HFSS 3D Layout
        print("Importing EDB file...")
        hfss3d_lo = ipk.create_3dlayout_project(edb_path=edb_file)
        hfss3d_lo.save_project()

        # Link EDB to IcePak
        print("Linking EDB file to IcePak...")
        ipk.create_pcb_from_3dlayout(
            component_name="PCB_pyAEDT",
            project_name=hfss3d_lo.project_file,
            design_name=hfss3d_lo.design_name,
            extent_type="Polygon",
            outline_polygon="poly_0",
            power_in=0,
            close_linked_project_after_import=False,
        )

        # Assign power losses to specific devices and define monitor points
        print("Assigning power losses and defining monitors...")
        monitors = []
        for designator, power in device_losses.items():
            device = ipk.modeler[designator]
            if device:
                # Assign power loss
                ipk.create_source_block(object_name=designator, input_power=power)

                # Automatically identify the top and bottom faces
                faces = device.faces
                top_face = max(faces, key=lambda f: f.center[2])  # Highest Z coordinate
                bottom_face = min(faces, key=lambda f: f.center[2])  # Lowest Z coordinate

                # Add monitors to the top and bottom faces
                top_monitor = ipk.monitor.assign_face_monitor(
                    face_id=top_face.id,
                    monitor_quantity="Temperature",
                    monitor_name=f"{designator}_Top_Monitor",
                )
                bottom_monitor = ipk.monitor.assign_face_monitor(
                    face_id=bottom_face.id,
                    monitor_quantity="Temperature",
                    monitor_name=f"{designator}_Bottom_Monitor",
                )
                monitors.append({"designator": designator, "top": top_monitor, "bottom": bottom_monitor})
            else:
                print(f"Warning: Device '{designator}' not found in the model.")

        # Setup the project for natural convection
        print("Setting up the simulation...")
        setup = ipk.create_setup()
        setup.props["Flow Regime"] = "Turbulent"
        setup.props["Ambient Temperature"] = "20cel"  # Ambient temperature
        setup.props["Convergence Criteria - Max Iterations"] = 100
        ipk.save_project()

        # Solve the project
        print("Solving the simulation...")
        ipk.analyze(setup=setup.name)

        # Extract monitor temperatures
        print("Extracting results...")
        results = []
        for monitor in monitors:
            top_temp = ipk.post.evaluate_monitor_quantity(monitor=monitor["top"], quantity="Temperature")["Mean"]
            bottom_temp = ipk.post.evaluate_monitor_quantity(monitor=monitor["bottom"], quantity="Temperature")["Mean"]
            power_loss = float(device_losses[monitor["designator"]][:-1])  # Remove "W" from the power loss
            temp_rise = top_temp - bottom_temp
            psi = temp_rise / power_loss
            results.append({"Device": monitor["designator"], "Top Temp (C)": top_temp, "Bottom Temp (C)": bottom_temp,
                            "Temp Rise (C)": temp_rise, "Psi (K/W)": psi})

        # Save results to CSV
        print(f"Saving results to {output_csv}...")
        with open(output_csv, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["Device", "Top Temp (C)", "Bottom Temp (C)", "Temp Rise (C)", "Psi (K/W)"])
            writer.writeheader()
            writer.writerows(results)

        print("Simulation and results processing complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Release AEDT
        ipk.release_desktop()
        print("IcePak simulation setup complete.")

# Example usage:
project_folder = "path_to_project_folder"
idf_file = "path_to_idf_file"
bdf_file = "path_to_bdf_file"
edb_file = "path_to_edb_file"
output_csv = "path_to_output_csv_file"
device_losses = {"Q1": "5W"}  # Example losses

setup_solve_and_export_results(
    project_folder, idf_file, bdf_file, edb_file, device_losses, output_csv
)
