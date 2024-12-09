import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft
from scipy.interpolate import interp1d
from scipy.signal import find_peaks
from tabulate import tabulate

plt.rcParams.update({'font.size': 12})  # Sets base font size

# Buck converter parameters
Vin = 450  # Input voltage
Vout = 96.0  # Output voltage
L = 150e-6  # Inductance
C = 47e-6  # Capacitance
R = 3.2    # Load resistance
fsw = 100e3 # Switching frequency

# Time parameters
t_sim = 3 * (1/fsw)  # Simulation time (10 switching periods)
dt = 1e-7            # Time step
t = np.arange(0, t_sim, dt)

# Initialize arrays
i_L = np.zeros_like(t)
i_switch = np.zeros_like(t)
i_diode = np.zeros_like(t)

# Duty cycle
D = Vout / Vin

# Initial conditions
i_L[0] = Vout / R  # Assume steady-state average inductor current

# Simulation loop
for n in range(1, len(t)):
    # Determine if switch is on or off
    if (t[n] % (1/fsw)) < (D * (1/fsw)):
        # Switch ON
        di_L = (Vin - Vout) * dt / L
        i_L[n] = i_L[n-1] + di_L
        i_switch[n] = i_L[n]
        i_diode[n] = 0
    else:
        # Switch OFF
        di_L = -Vout * dt / L
        i_L[n] = i_L[n-1] + di_L
        i_switch[n] = 0
        i_diode[n] = i_L[n]

currents = [i_L, i_switch, i_diode]
titles = ['Inductor Current', 'Switch Current', 'Diode Current']

# Modified FFT function with upsampling and peak detection
def perform_fft_with_peaks(signal, t, min_peak_height=0.1):
    # Upsampling
    t_upsampled = np.linspace(t[0], t[-1], len(t)*10)
    interpolator = interp1d(t, signal, kind='cubic')
    signal_upsampled = interpolator(t_upsampled)
    
    N = len(signal_upsampled)
    dt_upsampled = (t[-1] - t[0]) / N
    yf = fft(signal_upsampled)
    xf = np.linspace(0.0, 1.0/(2.0*dt_upsampled), N//2)
    magnitude_spectrum = 2.0/N * np.abs(yf[0:N//2])
    
    # Find peaks
    peaks, _ = find_peaks(magnitude_spectrum, height=min_peak_height)
    peak_freqs = xf[peaks]
    peak_magnitudes = magnitude_spectrum[peaks]
    
    # Sort peaks by magnitude
    sort_idx = np.argsort(peak_magnitudes)[::-1]  # Sort in descending order
    peak_freqs = peak_freqs[sort_idx]
    peak_magnitudes = peak_magnitudes[sort_idx]
    
    return xf, magnitude_spectrum, peak_freqs, peak_magnitudes

# Create the subplots
fig, axs = plt.subplots(3, 2, figsize=(15, 15))

# Process and plot each current
for i, (current, title) in enumerate(zip(currents, titles)):
    # Time domain plot
    axs[i, 0].plot(t*1e6, current)
    axs[i, 0].set_xlabel('Time (µs)')
    axs[i, 0].set_ylabel('Current (A)')
    axs[i, 0].set_title(f'{title} (Time Domain)')
    axs[i, 0].grid(True)

    # Frequency domain plot with peak detection
    xf, yf, peak_freqs, peak_mags = perform_fft_with_peaks(current, t)
    axs[i, 1].semilogy(xf/1e3, yf)
    axs[i, 1].set_xlabel('Frequency (kHz)')
    axs[i, 1].set_ylabel('Magnitude')
    axs[i, 1].set_title(f'{title} Spectrum')
    axs[i, 1].set_xlim(0, 500)  # Limit x-axis to 500 kHz
    axs[i, 1].grid(True)
    
    # Mark peaks on the plot
    axs[i, 1].plot(peak_freqs/1e3, peak_mags, 'ro')

    # Print peak analysis
    print(f"\n{title} Frequency Analysis:")
    
    # Calculate relative percentages
    total_magnitude = np.sum(peak_mags)
    relative_percentages = (peak_mags / total_magnitude) * 100
    
    # Create table data
    table_data = []
    for j in range(min(len(peak_freqs), 10)):  # Show top 10 peaks
        table_data.append([
            f"{peak_freqs[j]/1e3:.1f}",  # Frequency in kHz
            f"{peak_mags[j]:.3f}",       # Absolute magnitude
            f"{relative_percentages[j]:.1f}"  # Relative percentage
        ])
    
    # Print table using tabulate
    headers = ["Frequency (kHz)", "Magnitude", "Relative %"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

plt.tight_layout()
plt.show()

# Calculate and print ripple current
i_L_max = np.max(i_L)
i_L_min = np.min(i_L)
ripple_current = i_L_max - i_L_min
print(f"\nInductor current ripple: {ripple_current:.3f} A")

# Calculate and print average currents
i_L_avg = np.mean(i_L)
i_switch_avg = np.mean(i_switch)
i_diode_avg = np.mean(i_diode)
print(f"Average inductor current: {i_L_avg:.3f} A")
print(f"Average switch current: {i_switch_avg:.3f} A")
print(f"Average diode current: {i_diode_avg:.3f} A")
