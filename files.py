import os
import sys
root_path = os.path.dirname(os.path.realpath(sys.argv[0]))
settings_path = os.path.join(root_path, "scoreboard_settings.json")
secrets_path = os.path.join(root_path, "secrets.txt")
requirements_path = os.path.join(root_path, "requirements.txt")
settings_template_path = os.path.join(
    root_path, "scoreboard_settings.json.template")
log_path = os.path.join(root_path, "../scoreboard_log")
wpa_template = os.path.join(root_path, "wpa_supplicant.conf.template")
wpa_path = os.path.join(root_path, "wpa_supplicant.conf")
hotspot_on = os.path.join(root_path, "hotspot_on.sh")
hotspot_off = os.path.join(root_path, "hotspot_off.sh")
small_font = os.path.join(root_path, "fonts/4x6.pil")
big_font = os.path.join(root_path, "fonts/5x8.pil")
biggest_font = os.path.join(root_path, "fonts/7x13.pil")
