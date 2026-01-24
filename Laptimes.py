import fastf1 as f1
import pandas as pd
import numpy as np
import fastf1.plotting
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as goq


# Set dark background and white text for all plots
plt.style.use('dark_background')
FUEL_EFFECT_PER_LAP = 0.06 

f1.Cache.enable_cache('data')
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

def get_session():
    year = int(input("Enter year (2022-2025): "))
    if (year < 2022) or (year > 2025):
        print("Year must be between 2022 and 2025.")
        get_session()
    else: 
        schedule = fastf1.get_event_schedule(year)
        race_list = schedule[schedule['EventFormat'] != 'testing']
        
        for i, round_name in enumerate(race_list['EventName'], 1):
            print(f"{i}. {round_name}")
        
        race_idx = int(input("\nSelect race number: ")) - 1
        race_name = race_list.iloc[race_idx]['EventName']
        
        print(f"Loading {year} {race_name}...")
        session = fastf1.get_session(year, race_name, 'R')
        return session, year

def get_driver():
    drivers_df = race.results[['Abbreviation', 'FullName', 'TeamName']]
    print("\nDrivers:\n", drivers_df.to_string(index=False))
    driver_code = input("\nEnter first driver abbreviation: ").upper()
    return driver_code

# Loads the desired race
race, year = get_session()
race.load()
all_laps = race.laps.copy()

fastest_laps = all_laps.groupby('LapNumber').agg({'LapTime': 'min', 'Driver': 'first'}).reset_index()
fastest_laps.rename(columns={'LapTime': 'FastestLapTime', 'Driver': 'FastestDriver'}, inplace=True)

driver = get_driver()

driver_laps = race.laps.pick_drivers(driver).pick_quicklaps().reset_index()
total_laps = driver_laps['LapNumber'].max()
driver_laps = pd.merge(driver_laps, fastest_laps, on='LapNumber')

driver_laps['DeltaToFastest'] = (driver_laps['LapTime'] - driver_laps['FastestLapTime']).dt.total_seconds()

def calculate_fuel_correction(row):
    laps_remaining = total_laps - row['LapNumber']
    correction = pd.Timedelta(seconds=laps_remaining * FUEL_EFFECT_PER_LAP)
    return row['LapTime'] - correction

fuelCorrected = driver_laps.copy()
fuelCorrected['FuelCorrectedLapTime'] = fuelCorrected.apply(calculate_fuel_correction, axis=1)



# Get driver team color
driver_team_color = fastf1.plotting.get_driver_color(driver, race)

# Get pit stop laps
all_driver_laps = race.laps.pick_drivers(driver)
pit_stops = driver_laps[driver_laps['PitInTime'].notna()]
pit_laps = pit_stops['LapNumber'].values


def format_timedelta(td):
    if pd.isna(td): return ""
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"

driver_laps['LapTimeStr'] = driver_laps['LapTime'].apply(format_timedelta)
driver_laps['FuelCorrectedStr'] = fuelCorrected['FuelCorrectedLapTime'].apply(format_timedelta)


fig, ax = plt.subplots(figsize=(20, 10))

sns.scatterplot(data=driver_laps,
                x="LapNumber",
                y="LapTime",
                ax=ax,
                hue="Compound",
                palette=fastf1.plotting.get_compound_mapping(session=race),
                s=80,
                linewidth=0,
                legend='auto',
                alpha=0.6)

sns.lineplot(data=fuelCorrected, 
             x="LapNumber", 
             y="FuelCorrectedLapTime", 
             ax=ax,
             hue="Stint", # This breaks the line at each pit stop
             palette=['white', 'white', 'white'], # Keeps the line white
             legend=False,
             linewidth=2)

stints = fuelCorrected['Stint'].unique()



for stint in stints:
    
    stint_data = fuelCorrected[fuelCorrected['Stint'] == stint]
    
   
    clean_stint_data = stint_data[
        (stint_data['PitInTime'].isna()) & 
        (stint_data['PitOutTime'].isna()) &
        (stint_data['LapNumber'] < total_laps)
    ]

    # Only perform fit if we still have enough data points (at least 2)
    if len(clean_stint_data) > 1:
        x_clean = clean_stint_data['LapNumber']
        y_clean = clean_stint_data['FuelCorrectedLapTime'].dt.total_seconds()
        
        # Linear regression on CLEAN data
        m, c = np.polyfit(x_clean, y_clean, 1)
        
        # We still want to plot the trendline across the WHOLE stint 
        # range so it looks continuous on the graph
        x_plot = stint_data['LapNumber']
        trendline_y = m * x_plot + c
        
        ax.plot(x_plot, pd.to_timedelta(trendline_y, unit='s'), 
                color=driver_team_color, 
                linewidth=3, 
                label=f"Stint {stint} Deg: {m:.3f}s/lap")
# sphinx_gallery_defer_figures

###############################################################################
# Make the plot more aesthetic.
ax.set_xlabel("Lap Number")
ax.set_ylabel("Lap Time")

# The y-axis increases from bottom to top by default
# Since we are plotting time, it makes sense to invert the axis
ax.invert_yaxis()

# Add dashed vertical lines for pit stops in team color
for pit_lap in pit_laps:
    ax.axvline(x=pit_lap, color=driver_team_color, linestyle='--', linewidth=2, alpha=0.7, label='Pit Stop')


# Create a custom legend handle
custom_lines = [Line2D([0], [0], color='white', lw=2)]

# Get the existing handles and labels from the scatter plot (the tires)
handles, labels = ax.get_legend_handles_labels()

# Add our custom line to the list
handles.append(custom_lines[0])
labels.append("Fuel Corrected Lap Time")

# Re-apply the legend with the new combined list
ax.legend(handles=handles, labels=labels)

plt.suptitle(f"{driver} Laptimes in the {year} {race.event['EventName']}")
plt.grid(color='w', which='major', axis='both')
sns.despine(left=True, bottom=True)

plt.tight_layout()


# Create the interactive Plotly figure
fig_interactive = px.scatter(
    driver_laps, 
    x="LapNumber", 
    y="DeltaToFastest", 
    color="Compound",
    title=f"{driver} Delta to Session Leader - {year} {race.event['EventName']}",
    hover_data={
        "LapNumber": True,
        "DeltaToFastest": ":.3f",
        "LapTime": True,
        "FastestDriver": True  # This shows who set the fastest lap!
    },
    template="plotly_dark"
)

# Customizing the layout to match your F1 style
fig_interactive.update_yaxes(autorange="reversed", title_text="Seconds Behind Leader")
fig_interactive.update_xaxes(title_text="Lap Number")

# Add the 0.0 baseline
fig_interactive.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Pace Leader")

# Show the plot
fig_interactive.show()
plt.show()