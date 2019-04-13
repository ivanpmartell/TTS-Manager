# TTS-Manager

Import/Export Mods from Tabletop Simulator, including all assets.

## Status

Currently this code is rather alpha quality. It has also only been tested on a limited number of mods and machines. **Do not rely on this to backup your files without checking it restores correctly on another install.** If you find a configuration / mod that doesn't work, please let me know.

Listing, export and import all should work. Note that old-style mods (`.cjc` files) are *not* supported - they simply will not be listed.

To export a mod, you ideally should have downloaded *all* assets. Opening a mod in Tabletop Simulator is usually enough, but make sure you have taken something out of every bag in the mod. If anything is missing, then the tool will tell you. TTS Manager can attempt to download the files for you, but this feature is very new.

## GUI Quick Start

Download the installer from the [releases](https://github.com/cwoac/TTS-Manager/releases) and install it. Then run the gui from the created shortcut link.

### Command Line

Run the following to build and install the CLI on your machine.

``` PowerShell
python setup.py build
python setup.py install
```

To run and see the help.

``` PowerShell
tts-manager.exe -h
```

List all the mods in the workshop.

``` PowerShell
tts-manager.exe list
```

Export a mod with a forced download of all assets.

``` PowerShell
tts-manager.exe export -o E:\tts -d 12345678
```


Run the installed `tts_cli.exe` from within a command window. Use `tts_cli list` to find the id number of the mod to export then `tts_cli export id` to create a `.pak` file. You can then import this into an install using `tts_cli import path/to/pakfile`. The commands have further options, use `-h` to find out.

If you have set Tabletop Simulator to store mod files in its install directory, you will need to tell it where to find the files. Either run the gui and set the preferences there, or use `tts_cli config`.


## Requirements

Either download a compiled exe, or run using python3.

## TODO

These are primarily tracked on GitHub, but roughly:

- Uninstalling paks
- A better gui
- downloading arbitary pak files
- LOTS MORE TESTING.
