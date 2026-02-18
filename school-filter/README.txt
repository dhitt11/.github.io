======================================================
  SCHOOL TIME FILTER — Parental Control DNS Filter
======================================================

WHAT IT DOES
------------
During school hours, ONLY the websites you list in
config.json will work. Everything else (YouTube, gaming
sites, AI chatbots, social media, etc.) is automatically
blocked. Outside school hours, all websites work normally.

It also blocks kids from bypassing the filter by changing
DNS settings themselves (via Windows Firewall rules).


REQUIREMENTS
------------
- Windows 10 or Windows 11
- Administrator account on the child's computer
- Python 3.8 or newer  →  https://www.python.org/downloads/
  (check "Add Python to PATH" during Python install!)
- Internet connection during install (to download dnslib)


HOW TO INSTALL  (do this on each child's computer)
---------------------------------------------------
1. Copy this entire "school-filter" folder to the computer
   (USB drive, shared folder, email attachment, etc.)

2. Edit config.json FIRST (see "CUSTOMIZING" below)
   - Add your school's website domains
   - Adjust school hours if needed

3. Right-click  install.bat  →  "Run as administrator"

4. Follow the on-screen prompts. That's it!

The filter starts immediately and will auto-start every
time Windows boots — no action needed from you.


CUSTOMIZING  (config.json)
--------------------------
Open config.json with Notepad. Two main sections:

  1. school_hours
     Change start/end times for each day.
     Set a day to null (no quotes) to allow all sites that day.
     Example for a half-day Wednesday:
       "wednesday": { "start": "08:00", "end": "12:00" }

  2. allowed_domains
     List every website your kids need for school.
     Use *.example.com to allow a site AND all its subdomains.
     Use example.com alone to allow only that exact address.

     Common entries to add:
       - Your school's main domain  (e.g., "*.lincoln-k12.edu")
       - Any learning platform      (e.g., "*.canvas.net")
       - Typing practice sites      (e.g., "typing.com")
       - Approved research tools    (e.g., "*.britannica.com")

     To FIND your school's domain: look at the web address
     when your child logs into their school portal. The part
     after "https://" and before the next "/" is the domain.

  After editing config.json, the filter reloads it
  automatically within 5 minutes — no restart needed.

  NOTE: If the install has already been run, the config
  lives at:  C:\Program Files\SchoolFilter\config.json
  You must be logged in as Administrator to edit it there.


VIEWING THE LOG
---------------
To see which sites were blocked and when:
  C:\Program Files\SchoolFilter\filter.log

Open with Notepad. Blocked entries look like:
  2024-09-03 09:14:22  INFO     BLOCKED  youtube.com
  2024-09-03 09:14:45  INFO     BLOCKED  fortnite.com


HOW TO UNINSTALL
----------------
Right-click  uninstall.bat  →  "Run as administrator"
This removes the filter, restores DNS, and removes all rules.


TROUBLESHOOTING
---------------
Q: A school website is blocked during school hours.
A: Add it to the allowed_domains list in config.json.
   Wait 5 minutes, or restart the filter task:
   Open Task Scheduler → find "SchoolTimeFilter" → Run

Q: The filter doesn't seem to be running.
A: Open Task Scheduler (search for it in Start menu).
   Find "SchoolTimeFilter" and check its status.
   If it shows "Disabled", right-click → Enable.
   Then right-click → Run.

Q: My child changed the DNS settings back.
A: The firewall rules should prevent this, but if bypassed:
   - Re-run install.bat to reinstall
   - Consider creating a separate limited Windows user
     account for your child (no admin access)
   - Set a BIOS/UEFI password to prevent boot changes

Q: Windows says "Python not found" during install.
A: Download Python from https://www.python.org/downloads/
   During install, CHECK the box "Add Python to PATH"
   Then run install.bat again.

Q: The filter blocks Windows Update.
A: The default config allows microsoft.com and
   windowsupdate.com. If still blocked, add:
     "*.delivery.mp.microsoft.com"
   to allowed_domains in config.json.


SECURITY NOTES
--------------
- The filter requires Python to be installed. A determined
  teenager might try to uninstall Python. Consider locking
  down the Programs & Features control panel.

- The strongest protection is creating a standard (non-admin)
  Windows user account for your child. This prevents them
  from uninstalling software or changing system settings.
  You keep the Administrator password to yourself.

- The filter.log file shows you exactly what sites were
  attempted — useful for conversations with your kids.

- This tool blocks by DNS name (domain), not by IP address.
  Very determined users could use a VPN to bypass it.
  For younger children this is unlikely to be an issue.


FILES IN THIS FOLDER
--------------------
  filter.py    — The main program (Python script)
  config.json  — Your settings (hours, allowed sites)
  install.bat  — Run once to install on a computer
  uninstall.bat — Run to completely remove the filter
  README.txt   — This file


======================================================
