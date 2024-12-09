import numpy as np

# Buck converter operating conditions
Vin = 400  # Input voltage (V)
Vout = 48  # Output voltage (V)
Iout = 10  # Output current (A)
D = Vout / Vin  # Duty cycle

# Constants and parameters 
Vds = Vin  # Drain-to-source voltage (V)
Ipeak = Iout / D  # Peak current through HS switch (A)
Ids = Ipeak / 2  # Average current during switching
Rgon = 0.2  # Gate resistance during turn-on (ohms)
Rgoff = 0.1  # Gate resistance during turn-off (ohms)
Vdr_on = 7  # Gate drive voltage during turn-on (V)
Vdr_off = -3  # Gate drive voltage during turn-off (V)
Vth = 1.3  # Threshold voltage (V)
Vgsmiller = 3.0  # Miller plateau voltage (V)
gfs = 100  # Transconductance (S), typical estimated value
fsw = 100e3  # Switching frequency (Hz)
Ls = 0.5e-9  # Common source inductance (H)
Rds_on = 50e-3  # On-state resistance (ohms)

# Capacitances (from datasheet in farads)
Ciss_hv = 235e-12
Coss_hv = 60e-12
Crss_hv = 0.6e-12
Ciss_lv = 235e-12
Coss_lv = 60e-12
Crss_lv = 80e-12

# Derived capacitances at high and low voltages
Cgshv, Cgdhv = Ciss_hv - Crss_hv, Crss_hv
Cgslv, Cgdlv = Ciss_lv - Crss_lv, Crss_lv

# Helper functions for dynamic values
Crss_dynamic = lambda Vds: 5.679e-10 * (Vds ** -0.7523)  # Equation (12)

def turn_on_loss():
    # Stage t0 to t1
    ton1_t0 = -Rgon * (Cgdhv + Cgshv) * np.log(1 - (Vth - Vdr_off) / (Vdr_on - Vdr_off))

    # Stage t1 to t2
    ton2_t1 = (Ids * (Rgon * (Cgdhv + Cgshv) + Ls * gfs)) / ((Vdr_on - Vgsmiller) * gfs)

    # Stage t2 to tP
    depth = 0.9
    Qsto = (Coss_lv + Crss_lv) * (1 - depth) * Vds  # Adjusted dynamic capacitance
    di_dt = Ids / ton2_t1
    Isto = np.sqrt(max(Qsto * di_dt, 0))  # Ensure non-negative value
    Vgsmiller_peak = Isto / gfs + Vgsmiller
    tonP_t1 = (Ids * (Rgon * (Cgdhv + Cgshv) + Ls * gfs)) / ((Vdr_on - Vgsmiller_peak) * gfs)

    # Stage tP to tD
    Igdon = (Vdr_on - Vgsmiller) / Rgon
    Crss_prime = Crss_dynamic(Vds)
    tonD_tP = Crss_prime * Vds / Igdon

    # Stage tP to t3
    ton3_tP = Cgdlv * (1 - depth) * Vds * Rgon / (Vdr_on - Vgsmiller)

    # Stage t3 to t4
    ton4_t3 = -Rgon * (Cgdlv + Cgslv) * np.log(1 - depth * (Vdr_on - Vgsmiller) / (Vdr_on - Vdr_off))

    # Total turn-on time
    Pon = (
        Vds * (Ids + Isto) * (tonP_t1 / 2) +
        Vds * Isto * (tonD_tP / 3) +
        Vds * Ids * (tonD_tP / 2)
    ) * fsw

    return max(Pon, 0)  # Ensure non-negative loss

def turn_off_loss():
    depth = 0.9
    # Stage t0 to t1
    toff1_t0 = -Rgoff * (Cgdlv + Cgslv) * np.log((Vdr_on - Vgsmiller) / (Vdr_on - Vdr_off))

    # Stage t1 to t2
    toff2_t1 = (Cgdlv * Vds * Rgoff) / ((0.5 * (Vgsmiller + Vth) - Vdr_off))

    # Stage t2 to t3
    toff3_t2 = -Rgoff * (Cgdhv + Cgshv) * np.log((Vth - Vdr_off) / (depth * Vth - Vdr_off))

    # Total turn-off loss
    Poff = (Vds * Ids / 6) * max(toff2_t1, 0) * fsw

    return max(Poff, 0)  # Ensure non-negative loss

def conduction_loss():
    # Conduction loss calculation
    Pcond = Iout**2 * Rds_on * D
    return Pcond

# Calculate losses
Pon = turn_on_loss()
Poff = turn_off_loss()
Pcond = conduction_loss()

# Total switching and conduction loss
Ptotal = Pon + Poff + Pcond

# Display results
print(f"Turn-on loss (Pon): {Pon:.3f} W")
print(f"Turn-off loss (Poff): {Poff:.3f} W")
print(f"Conduction loss (Pcond): {Pcond:.3f} W")
print(f"Total loss (Ptotal): {Ptotal:.3f} W")
