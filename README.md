# Journey Map Data Merger
Merge Map Tiles, NBT Data (Waypoints), Region Cache, JSON Data (Addons), and *all other files* from multiple people, timestamps, or devices - effortlessly.

## Overview
This tool is a ground-up re-write of Lopolin-LP's original
[journeymap-data-merger](https://github.com/Lopolin-LP/journeymap-data-merger), redesigned to be:

- Easier to install
- Easier to use
- More robust
- More feature-complete

It now supports ZIP input/output, region caches (.mca files), mod addon data (JSON), arbitrary NBT/JSON, and all other file types!

---

### New Features:
- **Less External Dependencies**
  Replaced ImageMagick with the pillow python package, and the crashing amulet-nbt with nbt-lib

- **ZIP input & output**
  - Accepts ZIPs as input
  - Can output a ZIP directly (using the `--zip` flag or using a `.zip` output path)

- **Duplicate input detection**
  Automatically ignores repeated folder paths.

- **Region cache merging**
  File-level merging for `.mca` region files (newest wins).

- **Addon JSON merging**
  Merges all JSON files (Typically found in the addon folder and waypoint backups).

- **"Other" file merging**
  A new mode that merges *all remaining file types* using newest-wins logic.


### To Do:
- [ ] Deep Merging of NBT files
- [ ] Deep Merging of JSON files (Currently uses only IDs to merge)

---

## Video
Here is Lopolin-LP's original explanation/tutorial video as a temporary solution until I make one.
*(Note: installation and usage differ slightly from my version - use the text guide below.)*

<div style='display: flex; justify-content: center;'>
  <a style='width: 50%;' href='https://youtu.be/0U_hZx94AL4' target='_blank'>
    <img src='./thumbnail.png'>
  </a>
</div>

---

## Installation & Usage

1. Install [Python 3.13](https://www.python.org/) - [MS Store](https://apps.microsoft.com/detail/9pnrbtzxmb4z?hl=en-US&gl=US) *(A restart is required after installation.)*
2. Download and extract the project files.
3. Open a terminal (CMD/PowerShell) inside the extracted folder.
4. Create a python virtual environment `python -m venv jmmenv`
5. Activate the environment `jmmenv\Scripts\activate`
5. Install the dependencies `pip install -r requirements.txt`
7. Run the script: `python JourneyMapMerger.py "<Output Path>" "<Input Path>" "<Input Path...>"` (use as many inputs as you need)
8. Confirm prompts and wait for merging to complete
9. When complete, import the output folder/ZIP into JourneyMap or manually place it in your JourneyMap directory.

---

## Finding JourneyMap Folders

### Option 1 - Export (Easy)
1. Load into the Minecraft world/server.
2. Open JourneyMap settings (e.g., via fullscreen map).
3. Select **Import/Export** at the bottom.
4. Export your data somewhere memorable.

### Option 2: Grabbing the Folder Directly
Wherever your minecraft profile is saved (I assume `.minecraft` for this), you also have your mods and other things saved. In there, alongside the `mods` folder, there is `journeymap`. The folder structure is something like this:
```
journeymap/
  data/
    mp/
      <server-name-or-identifier>/
        overworld/
        the_end/
        the_nether/
        waypoints/
          backup/
            WaypointData.dat
          WaypointData.dat
        addon-data/
    sg/
      <world-name-or-identifier>/
        (same structure as mp)
```

The folder with the identifier (server name or world name) is the **root** you should use as an input path.

So for a Multiplayer Server with the name `My server` and your friend calling it `absolute cinema` you both have that servers data saved in `.minecraft/journeymap/data/mp/My~server/` and `.minecraft/journeymap/data/mp/absolute~cinema/` respectively.

## Replacing JourneyMap Data

### Option 1 - Import (Easy)
Use the same steps as exporting, but choose **Import** instead.
*(This replaces all existing JourneyMap data.)*

### Option 2 - Replace the Folder
Move the merged output folder into the same location as your original JourneyMap data.
*(Remeber to rename or back up the old one first.)*

---

## Command-Line Flags
The merger supports several optional flags that let you control exactly what gets merged and how the output is produced.

### Merge Selection Flags
Choose which data types to merge:

| Flag                | Description                                             |
|---------------------|---------------------------------------------------------|
| `-m`, `--maps`      | Merge **map tiles** (`.png`).                           |
| `-r`, `--regions`   | Merge **region cache** (`.mca`).                        |
| `-n`, `--nbt`       | Merge all **NBT** (waypoint) files (`.dat`, `.nbt`).    |
| `-j`, `--json`      | Merge all **JSON** (addon) files.                       |
| `-o`, `--other`     | Merge all **other** file types (newest wins).           |
| `-a`, `--all`       | Merge **everything** (maps, regions, NBT, JSON, other). |

If you specify none, the default is:
**maps + regions + nbt + json**

---

### Behavior Flags
These control how conflicts are resolved and how interactive the tool is.

| Flag          | Description                                                                                        |
|---------------|----------------------------------------------------------------------------------------------------|
| `--manual`    | Preserves input order. The **first** input wins when conflicts occur, instead of using timestamps. |
| `-y`, `--yes` | Automatically answers "yes" to all confirmation prompts. Useful for automation or scripts.         |

---

#### ZIP Flags
These control ZIP input/output behavior.
| Flag          | Description                                                                                      |
|---------------|--------------------------------------------------------------------------------------------------|
| `-z`, `--zip` | Outputs the merged result as a `.zip` file. Automatically cleans up the temporary output folder. |
| *(implicit)*  | If your output path ends with `.zip`, ZIP mode is enabled automatically (No flag needed.)        |

---

## Examples

Merge all basic files (default):
`python JourneyMapMerger.py "Merged" "JM1" "JM2"`

Merge only NBT files (waypoints):
`python JourneyMapMerger.py "Merged" "JM1" "JM2" --nbt`

Manual mode (first input wins):
`python JourneyMapMerger.py "Merged" "OldJM" "NewJM" --manual`

Output as ZIP:
`python JourneyMapMerger.py "Merged.zip" "JM1" "JM2"`

Merge absolutely everything:
`python JourneyMapMerger.py "Merged" "JM1" "JM2" --all`


---

## FAQ

### Does this modify my input folders?
No. It will even prevent you from doing so if the output overlaps the input folders. All merging happens in the output folder only.

### Can I merge more than two folders?
Yes. You can merge as many as you want: `python JourneyMapMerger.py "Merged" "JM1" "JM2" "JM3" "JM4"`

### Does order matter?
Only if you use the `--manual` flag. Otherwise, the **newest file wins**.

### Can I merge singleplayer and multiplayer data?
Yes, as long as the folder structure is valid.

### Does this work with mod integrations?
Maybe? I tested it using Minecolonies but that was it.

### Can I merge data from different Minecraft versions?
Generally yes, unless JourneyMap changes its internal formats.
