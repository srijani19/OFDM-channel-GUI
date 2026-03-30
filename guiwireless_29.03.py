import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


np.random.seed(0)
current_channel = None
current_params = None
Nsc = 1024

#channel_realization = 0
current_batch = 0

# channel_models = {
#     "COST 259": ["Urban", "Hilly", "Rural"],
#     "3GPP TDL": ["TDL-A", "TDL-B", "TDL-C"],
#     "3GPP CDL": ["CDL-A", "CDL-B", "CDL-C", "CDL-D", "CDL-E"]
# }
channel_models = {
    "COST.259": ["Urban", "Hilly", "Rural"],
    "3GPP.TR.38.901.TDL": ["TDL-A", "TDL-B", "TDL-C"],
    "3GPP.TR.38.901.CDL": ["CDL-A", "CDL-B", "CDL-C", "CDL-D", "CDL-E"]
}


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
#app.geometry("1150x720")
app.geometry("1350x800")
app.title("Wireless OFDM Channel GUI")



top_frame = ctk.CTkFrame(app, height=60)
top_frame.pack(fill="x", padx=10, pady=10)

for i in range(1, 5):
    ctk.CTkButton(top_frame, text=f"Button {i}", width=120).pack(
        side="left", padx=10, pady=10
    )



main_container = ctk.CTkFrame(app)
main_container.pack(fill="both", expand=True, padx=10, pady=10)

left_sidebar = ctk.CTkFrame(main_container, width=260)

left_sidebar.pack(side="left", fill="y", padx=10, pady=10)
left_sidebar.pack_propagate(False)


content_frame = ctk.CTkFrame(left_sidebar)
content_frame.pack(fill="both", expand=True)


button_frame = ctk.CTkFrame(left_sidebar)
button_frame.pack(fill="x", pady=10, padx=10, side="bottom")

work_area = ctk.CTkFrame(main_container)
work_area.pack(side="left", fill="both", expand=True, padx=10, pady=10)


selected_channel_type = "COST.259"
selected_channel_subtype = channel_models["COST.259"][0]



def format_sci(value):
    """Format number in compact scientific notation"""
    if value == 0:
        return "0"
    return f"{value:.2e}".replace("e+0", "e").replace("e+", "e")


def on_channel_type_change(choice):
    global selected_channel_type, selected_channel_subtype, current_params

    selected_channel_type = choice
    selected_channel_subtype = channel_models[choice][0]

    # Update subtype dropdown values
    channel_subtype_menu.configure(values=channel_models[choice])
    channel_subtype_menu.set(selected_channel_subtype)

    # Enable/disable L slider
    if selected_channel_type == "COST.259":
        L_slider.configure(state="normal")
    else:
        L_slider.configure(state="disabled")

    current_params = None

    for s in sliders:
        s.configure(state="disabled")
    for e in entries:
        e.configure(state="disabled")

    prev_button.configure(state="disabled")
    next_button.configure(state="disabled")
   # Handle DS enable/disable
    if selected_channel_type == "COST.259":
        DS_slider.configure(state="disabled")
        DS_entry.configure(state="disabled")
    else:
        DS_slider.configure(state="normal")
        DS_entry.configure(state="normal")
    update_plots()


def on_channel_subtype_change(choice):
    global selected_channel_subtype, current_params, current_batch

    selected_channel_subtype = choice
    current_batch = 0
    realization_label.configure(text="Realization: 0")

    if selected_channel_type == "COST.259":
        L_slider.configure(state="normal")
    else:
        L_slider.configure(state="disabled")

    current_params = None

    for s in sliders:
        s.configure(state="normal")
    for e in entries:
        e.configure(state="normal")
    # Override DS for COST
    if selected_channel_type == "COST.259":
        DS_slider.configure(state="disabled")
        DS_entry.configure(state="disabled")

    prev_button.configure(state="disabled")
    next_button.configure(state="normal")

    update_plots()



# Channel Type Dropdown
channel_type_menu = ctk.CTkOptionMenu(
    # left_sidebar,
    content_frame,
    values=list(channel_models.keys()),
    command=on_channel_type_change
)
channel_type_menu.set(selected_channel_type)
channel_type_menu.pack(pady=10, padx=10)


# Channel Subtype Dropdown
channel_subtype_menu = ctk.CTkOptionMenu(
    content_frame,
    values=channel_models[selected_channel_type],
    command=on_channel_subtype_change
)
channel_subtype_menu.set(selected_channel_subtype)
channel_subtype_menu.pack(pady=10, padx=10)

# Divider
ctk.CTkFrame(left_sidebar, height=2).pack(pady=10)


def get_params():
    Nsc = int(N_slider.get())
    Nsym = int(T_slider.get())
    fc = float(fc_slider.get())
    fd = float(fd_slider.get())
    B = int(B_slider.get())
    L = int(L_slider.get())
    DS = float(DS_slider.get())   # NEW
    return Nsc, Nsym, fc, fd, B, L, DS


def generate_ofdm_channel(Nsc, Nsym, fc, fd, B, L_user, DS, ch_type, ch_subtype):
    delta_f = 15e3
    Tfft = 1 / delta_f
    Tcp = Tfft / 8
    Tsym = Tfft + Tcp
    
    # Sampling frequency for the channel representation
    # We use a fixed reference or Nsc based reference
    Fs = Nsc * delta_f 
    
    base_seed = hash((fc, fd, ch_type, ch_subtype)) % (2**32)

    if ch_type == "COST.259":
        L = min(L_user, Nsc)
        if ch_subtype == "Urban": tau_rms = 2e-6
        elif ch_subtype == "Hilly": tau_rms = 5e-6
        else: tau_rms = 0.5e-6
        
        Ts = 1 / Fs
        delays = np.arange(L) * Ts
        power_profile = np.exp(-delays / tau_rms)
        delay_samples = np.arange(L) # Integer taps for COST
    
    elif "3GPP" in ch_type:
        # Load the correct TDL/CDL tables
        if "TDL-A" in ch_subtype:
            delays_norm = np.array([0.0000, 0.3819, 0.4025, 0.5868, 0.4610, 0.5375, 0.6708, 0.5750, 0.7618, 1.5375, 1.8978, 2.2242, 2.1718, 2.4942, 2.5119, 3.0582, 4.0810, 4.4579, 4.5695, 4.7966, 5.0066, 5.3043, 9.6586])
            powers_db = np.array([-13.4, 0, -2.2, -4, -6, -8.2, -9.9, -10.5, -7.5, -15.9, -6.6, -16.7, -12.4, -15.2, -10.8, -11.3, -12.7, -16.2, -18.3, -18.9, -16.6, -19.9, -29.7])
        elif "TDL-B" in ch_subtype:
            delays_norm = np.array([0.0000, 0.1072, 0.2155, 0.2095, 0.2870, 0.2986, 0.3752, 0.5055, 0.3681, 0.3697, 0.5700, 0.5283, 1.1021, 1.2756, 1.5474, 1.7842, 2.0169, 2.8294, 3.0219, 3.6187, 4.1067, 4.2790, 4.7834, 5.4143, 5.6753])
            powers_db = np.array([0, -2.2, -4, -3.2, -9.8, -1.2, -3.4, -5.2, -7.6, -3, -8.9, -9, -4.8, -5.7, -7.5, -1.9, -7.6, -12.2, -9.8, -11.4, -14.9, -9.2, -11.3, -12, -12.6])
        else: # Default/CDL logic
            delays_norm = np.array([0, 0.5, 1.0, 1.5, 2.0])
            powers_db = np.array([0, -3, -6, -9, -12])

        delays = delays_norm * DS
        power_profile = 10 ** (powers_db / 10)
        delay_samples = delays * Fs # This is fractional
        L = len(delays)

    power_profile /= np.sum(power_profile)
    H = np.zeros((B, Nsym, Nsc), dtype=complex)
    h_time_all = np.zeros((B, L, Nsym), dtype=complex)

    for b in range(B):
        np.random.seed(base_seed + b)
        g = (np.random.randn(L) + 1j*np.random.randn(L)) / np.sqrt(2)
        fd_l = fd * np.cos(2 * np.pi * np.random.rand(L))

        for n in range(Nsym):
            doppler = np.exp(1j * 2 * np.pi * fd_l * n * Tsym)
            h_t = np.sqrt(power_profile) * g * doppler
            h_time_all[b, :, n] = h_t
            
            # Use Frequency Domain construction for fractional delays
            # H(k) = sum_l { h_l * exp(-j*2*pi*k*delay_l / Nsc) } 
            # This is mathematically more accurate than padding a vector
            k_idx = np.arange(Nsc)
            for l in range(L):
                phase_shift = np.exp(-1j * 2 * np.pi * k_idx * delay_samples[l] / Nsc)
                H[b, n, :] += h_t[l] * phase_shift

    return h_time_all, H, delay_samples



def update_plots(*args):
    global current_channel, current_params, current_batch
    params = get_params()
    if params is None: return
    Nsc, Nsym, fc, fd, B, L, DS = params
    current_batch = min(current_batch, B-1)

    channel_signature = (params, selected_channel_type, selected_channel_subtype)
    if channel_signature != current_params or current_channel is None:
        current_channel = generate_ofdm_channel(Nsc, Nsym, fc, fd, B, L, DS, selected_channel_type, selected_channel_subtype)
        current_params = channel_signature

    h_time_all, H, delay_samples = current_channel
    h_time = h_time_all[current_batch]
    H_batch = H[current_batch]

    ax_cir.clear()
    ax_cfr.clear()

    # CIR PLOT
    for n in range(Nsym):
        ax_cir.stem(delay_samples, np.ones(len(delay_samples))*n, np.abs(h_time[:, n]), 
                    linefmt='b', markerfmt='bo', basefmt=" ")

    # The dynamic limit is key!
    max_d = np.max(delay_samples) if len(delay_samples) > 0 else 10
    ax_cir.set_xlim(0, max_d * 1.1)
    ax_cir.set_title(f"CIR (DS={DS:.2e}s)")

    # CFR PLOT
    K, N = np.meshgrid(np.arange(Nsc), np.arange(Nsym))
    Z = 20 * np.log10(np.abs(H_batch) + 1e-12)
    ax_cfr.plot_surface(K, N, Z, cmap='viridis')
    ax_cfr.set_title("3D CFR (Frequency Selectivity)")

    canvas_cir.draw()
    canvas_cfr.draw()

    
    
    


plot_frame = ctk.CTkFrame(work_area)
plot_frame.pack(fill="both", expand=True, padx=20, pady=20)

# fig_cir, ax_cir = plt.subplots(figsize=(4, 4))
# fig_cfr, ax_cfr = plt.subplots(figsize=(4, 4))

from mpl_toolkits.mplot3d import Axes3D

fig_cir = plt.figure(figsize=(5,4))
ax_cir = fig_cir.add_subplot(111, projection='3d')

fig_cfr = plt.figure(figsize=(5,4))
ax_cfr = fig_cfr.add_subplot(111, projection='3d')

canvas_cir = FigureCanvasTkAgg(fig_cir, master=plot_frame)
canvas_cfr = FigureCanvasTkAgg(fig_cfr, master=plot_frame)

canvas_cir.get_tk_widget().pack(side="left", fill="both", expand=True)
canvas_cfr.get_tk_widget().pack(side="left", fill="both", expand=True)





realization_label = ctk.CTkLabel(
   content_frame,
    #text=f"Realization: {channel_realization}"
    text=f"Realization: {current_batch}"
)

realization_label.pack(pady=10)



def next_realization():

    global current_batch

    B = int(B_slider.get())

    if current_batch < B - 1:
        current_batch += 1

    realization_label.configure(text=f"Realization: {current_batch}")

    # enable previous if we moved forward
    if current_batch > 0:
        prev_button.configure(state="normal")

    update_plots()



def previous_realization():

    global current_batch

    if current_batch > 0:
        current_batch -= 1

    realization_label.configure(text=f"Realization: {current_batch}")

    # disable previous if back to first
    if current_batch == 0:
        prev_button.configure(state="disabled")

    update_plots()


sliders = []
entries = []



def slider_input(label, from_, to_, initial, is_int=False, use_sci=False):
    
    frame = ctk.CTkFrame(content_frame)
    frame.pack(pady=8, padx=10, fill="x")

    top_row = ctk.CTkFrame(frame, fg_color="transparent")
    top_row.pack(fill="x", padx=5)

    label_widget = ctk.CTkLabel(top_row, text=label)
    label_widget.pack(side="left")

    entry = ctk.CTkEntry(
        top_row,
        width=80,
        height=28,
        fg_color="#1f1f1f",
        border_color="#4a90e2",
        border_width=2,
        text_color="white"
    )
    # entry.insert(0, str(initial))
    if use_sci:
        entry.insert(0, format_sci(initial))
    else:
        entry.insert(0, str(int(initial) if is_int else initial))

    entry.pack(side="right")   # ✅ always pack
    entry.configure(state="disabled")
    entries.append(entry)
        # =========================
    # SLIDER (FULL WIDTH BELOW)
    # =========================
    slider = ctk.CTkSlider(
        frame,
        from_=from_,
        to=to_,
        state="disabled"
    )
    slider.set(initial)
    slider.pack(fill="x", padx=5, pady=(5, 0))

   
    def on_slide(value):
        if is_int:
            value = int(value)
        else:
            value = float(value)

        # entry.delete(0, "end")
        # entry.insert(0, str(value))
        entry.delete(0, "end")
        if use_sci:
            entry.insert(0, format_sci(value))
        else:
            entry.insert(0, str(int(value) if is_int else value))
        update_plots()

    slider.configure(command=on_slide)


    def on_entry(event=None):
        try:
            # value = float(entry.get())
            value = float(entry.get().replace(" ", ""))
            value = max(from_, min(to_, value))

            if is_int:
                value = int(value)

            slider.set(value)
            # entry.delete(0, "end")
            # entry.insert(0, str(value))
            entry.delete(0, "end")
            if use_sci:
                entry.insert(0, format_sci(value))
            else:
                entry.insert(0, str(int(value) if is_int else value))

            update_plots()

        except ValueError:
            pass

    entry.bind("<Return>", on_entry)
    entry.bind("<FocusOut>", on_entry)

    sliders.append(slider)
    return slider,entry

fc_slider, fc_entry = slider_input("fc (Hz)", 1e9, 5e9, 2e9, use_sci=True)
fd_slider, fd_entry = slider_input("fd (Hz)", 0, 1000, 200)
N_slider, N_entry = slider_input("N subcarriers", 64, 1024, 128, is_int=True)
T_slider, T_entry = slider_input("N symbols", 1, 50, 14, is_int=True)
B_slider, B_entry = slider_input("Batch size", 1, 64, 16, is_int=True)
L_slider, L_entry = slider_input("Number of taps", 1, 64, 12, is_int=True)
DS_slider, DS_entry = slider_input("Delay Spread (s)", 1e-8, 5e-6, 1e-6)



# prev_button = ctk.CTkButton(
#     left_sidebar,
#     text="Previous",
#     command=previous_realization,
#     state="disabled"
# )

# prev_button.pack(pady=(20,5), padx=10, fill="x")


# next_button = ctk.CTkButton(
#     left_sidebar,
#     text="Next",
#     command=next_realization,
#     state="disabled"
# )

# next_button.pack(pady=(5,20), padx=10, fill="x")

# Frame for buttons (NEW)
# button_frame = ctk.CTkFrame(left_sidebar)
# button_frame.pack(pady=20, padx=10, fill="x")
# prev_button = ctk.CTkButton(button_frame, ...)
# next_button = ctk.CTkButton(button_frame, ...)

prev_button = ctk.CTkButton(
    button_frame,
    text="Previous",
    command=previous_realization,
    state="disabled"
)
prev_button.pack(side="left", expand=True, fill="x", padx=(0,5))

next_button = ctk.CTkButton(
    button_frame,
    text="Next",
    command=next_realization,
    state="disabled"
)
next_button.pack(side="right", expand=True, fill="x", padx=(5,0))



update_plots()



def on_closing():
    plt.close("all")
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

app.mainloop()



#Plotting tap index --Not actual delay positions