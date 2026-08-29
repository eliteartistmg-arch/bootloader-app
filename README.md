# bootloader-app

Motorola Bootloader Utility Pro is a small Tkinter-based utility for interacting with Motorola devices in fastboot and EDL modes, patching boot images, and running common bootloader-related workflows.

## Features

- Detects installed tools such as fastboot, EDL, Magisk, mtkclient, and blankflash
- Refreshes and inspects connected fastboot devices
- Unlocks or locks the bootloader
- Flash and back up partitions
- Supports EDL reboot and EDL flashing workflows
- Patches boot images with Magisk
- Runs exploit-oriented helper flows for common Motorola tasks

## Run from the repository

```bash
cd /workspaces/bootloader-app
./run_app.sh
```

Or directly:

```bash
cd /workspaces/bootloader-app
python3 bootloader_app.py
```

## Desktop shortcut

The repository includes a simple desktop launcher script that can be used from a Linux desktop environment.

1. Make sure the launcher is executable:
   ```bash
   chmod +x /workspaces/bootloader-app/run_app.sh
   ```
2. Create a .desktop entry in your desktop or application launcher directory, for example:
   ```ini
   [Desktop Entry]
   Version=1.0
   Type=Application
   Name=Motorola Bootloader Utility Pro
   Comment=Fastboot and EDL utility for Motorola devices
   Exec=/workspaces/bootloader-app/run_app.sh
   Icon=applications-system
   Terminal=true
   Categories=Utility;System;
   ```
3. Save it as `motorola-bootloader-utility-pro.desktop` and mark it executable:
   ```bash
   chmod +x ~/Desktop/motorola-bootloader-utility-pro.desktop
   ```

## Notes

This utility is intended for advanced device maintenance and may erase data or modify boot partitions. Use with caution and only on devices you own or are authorized to modify.
