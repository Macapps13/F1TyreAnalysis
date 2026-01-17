import fastf1 as f1
import pandas as pd
import fastf1.plotting
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

#Caches data for faster retrieval
f1.Cache.enable_cache('data')

def get_session():
    year = int(input("Enter year (2022-2025): "))
    schedule = fastf1.get_event_schedule(year)
    race_list = schedule[schedule['EventFormat'] != 'testing']
    
    for i, round_name in enumerate(race_list['EventName'], 1):
        print(f"{i}. {round_name}")
    
    race_idx = int(input("\nSelect race number: ")) - 1
    race_name = race_list.iloc[race_idx]['EventName']
    
    print(f"Loading {year} {race_name}...")
    session = fastf1.get_session(year, race_name, 'R')
    return session

def get_driver():
    drivers_df = session.results[['Abbreviation', 'FullName', 'TeamName']]
    print("\nDrivers:\n", drivers_df.to_string(index=False))
    driver_code = input("\nEnter first driver abbreviation: ").upper()
    return driver_code

# Loads the desired race
session  = get_session()
session.load()


# Extract only laps without major errors or missing sectors, and box stops
laps = session.laps.pick_accurate()
clean_laps = laps.pick_wo_box() 

driver = get_driver()
while True: 
    try: 
        driver_laps = clean_laps.pick_driver(driver)
        break
    except KeyError:
        print(f"Driver '{driver}' not found")
        driver = get_driver()

driver_info = session.results[session.results['Abbreviation'] == driver].iloc[0]
team_color = fastf1.plotting.get_team_color(driver_info['TeamName'], session=session)


# Plot 1: Lap Times Over the Race
plt.figure(figsize=(12, 6))
plt.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), marker='o', linestyle='-', linewidth=2, markersize=6, color = team_color)
plt.xlabel('Lap Number')
plt.ylabel('Lap Time (seconds)')
plt.title(f'{driver} - Lap Times Over the Race')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('laptimes_progression.png', dpi=300, bbox_inches='tight')
plt.show()

# Plot 2: Lap Times by Tyre Compound
plt.figure(figsize=(12, 6))
tyre_colors = {'SOFT': '#FF1800', 'MEDIUM': '#FFF200', 'HARD': '#F0F0F0'}
for compound in driver_laps['Compound'].unique():
    compound_laps = driver_laps[driver_laps['Compound'] == compound]
    plt.scatter(compound_laps['LapNumber'], compound_laps['LapTime'].dt.total_seconds(), 
                label=compound, s=100, color=tyre_colors.get(compound, '#808080'), alpha=0.7)

plt.xlabel('Lap Number')
plt.ylabel('Lap Time (seconds)')
plt.title(f'{driver} - Lap Times by Tyre Compound')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('laptimes_by_compound.png', dpi=300, bbox_inches='tight')
plt.show()

# Plot 3: Tyre Degradation by Compound
plt.figure(figsize=(12, 6))
for compound in driver_laps['Compound'].unique():
    compound_laps = driver_laps[driver_laps['Compound'] == compound].sort_values('LapNumber')
    plt.plot(compound_laps['LapNumber'], compound_laps['LapTime'].dt.total_seconds(), 
             marker='o', label=compound, linewidth=2, markersize=6)

plt.xlabel('Lap Number')
plt.ylabel('Lap Time (seconds)')
plt.title(f'{driver} - Tyre Degradation Analysis')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('tyre_degradation.png', dpi=300, bbox_inches='tight')
plt.show()

# Print summary statistics
print(f"\n=== Summary for {driver} ===")
print(f"Total laps: {len(driver_laps)}")
print(f"Fastest lap: {driver_laps['LapTime'].min()}")
print(f"Slowest lap: {driver_laps['LapTime'].max()}")
print(f"Average lap time: {driver_laps['LapTime'].mean()}")
print(f"\nTyre compounds used: {driver_laps['Compound'].unique()}")

