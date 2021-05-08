#!/usr/bin/python3

import argparse
import sys
import os
from pathlib import Path
import shutil
import subprocess

test_mode = False

lock_file = ".grab_running"
download_folder = "downloads"
generic_transfer_folder = "transfer"
radio_present_transfer_folder = "sounds"
tv_preset_transfer_folder = "transfer"

default_cmdline = "/usr/bin/get_iplayer --no-copyright"

radio_preset = [
    "Danny Howard",
    "Pete Tong", 
    "Radio 1's Essential Mix",
    "Diplo and Friends",
    "Radio 1's Residency",
    "Radio 1's Drum & Bass Show with Ren.* LaVice",
    "Radio 1's Drum & Bass Mix",
    ]

tv_preset = ["Panorama",
             "Horizon",
             "Call the Midwife: Series 10"]

default_quality = {"radio": "best", "tv": "good"}

list_format = { "full": "<pid>: <channel>: <available>: <name> - <episode>",
                "pid": "<pid>",
                "channel": "<channel>" }

def parse_arguments():
    global test_mode
    parser = argparse.ArgumentParser()
    cmd_group = parser.add_mutually_exclusive_group()
    cmd_group.add_argument("--download", action="store_true", help="Download programme(s)")
    cmd_group.add_argument("--list", action="store_true", help="Get a list of programme")
    cmd_group.add_argument("--latest", action="store_true", help="Get the latest based on the preset set of programmes")
    cmd_group.add_argument("--search", help="Search for a programme")
    args_group = parser.add_mutually_exclusive_group()
    args_group.add_argument("--pid", help="The pid of the programme to download")
    args_group.add_argument("--preset", action="store_true", help="Use a preset set of programmes")
    parser.add_argument("--type", choices=["radio", "tv"], required=True, help="Type of programme [default radio]")
    parser.add_argument("--channel", default="all", help="Scope to a channel")
    parser.add_argument("--quality", choices=["best", "better", "good", "worst"], help="Force the quality of the download")
    parser.add_argument("--since", type=int, default=7, help="Scope to the last [x] days")
    parser.add_argument("--force", action="store_true", help="Force an action")
    parser.add_argument("--test", action="store_true", help="Special test mode that doesn't execute download requests")
    args = parser.parse_args()
    test_mode = args.test
    return args

def do_download(programme_type, since, quality, force, pid, preset):
    if pid:
        download_by_pid(programme_type, quality, force, pid)
    elif preset:
        download_by_preset(programme_type, since, quality, force) 
    post_download(get_transfer_folder(programme_type, preset))

def do_list(programme_type, channel, since):
    search_term = ".*"
    output = query(programme_type, channel, since, search_term)
    print_list(output)

def do_search(programme_type, channel, since, search_term):
    output = query(programme_type, channel, since, search_term)
    print_list(output)

def do_latest(programme_type, since):
    channel = "all"
    search_term = get_preset_arg(programme_type)
    output = query(programme_type, channel, since, search_term)
    print_list(output)

def query(programme_type, channel, since, search_term, output_format="full"):
    global list_format
    type_arg = get_type_arg(programme_type)
    channel_arg = get_channel_arg(channel)
    since_arg = get_since_arg(since)
    listformat_arg = f"--listformat=\"{list_format[output_format]}\""
    extra_arg = f" --sort=available --fields=name"
    cmdline = f"{default_cmdline} {type_arg} {channel_arg} {since_arg} {listformat_arg} {extra_arg} \"{search_term}\""
    return execute_with_callback(cmdline, get_actual_output)

def download_by_pid(programme_type, quality, force, pid):
    quality_arg = get_quality_arg(programme_type, quality)
    force_arg = get_force_arg(force)
    output_arg = get_output_arg()
    cmdline = f"{default_cmdline} {quality_arg} {force_arg} --whitespace --fileprefix=\"<nameshort> <firstbcastdate> - <episodeshort>\" --pid={pid} {output_arg}"
    execute(cmdline)

def download_by_preset(programme_type, since, quality, force):
    pids = get_pids_from_preset(programme_type, since)
    for pid in pids:
        download_by_pid(programme_type, quality, force, pid)

def get_pids_from_preset(programme_type, since):
    channel = "all"
    search_term = get_preset_arg(programme_type)
    return query(programme_type, channel, since, search_term, output_format="pid")

def get_actual_output(output):
    processed_output = []
    lines = output.split('\n')
    i = 0
    while (i < len(lines)):
        if lines[i].startswith("Matches:"):
            i += 1
            while (not lines[i].startswith("INFO:")):
                processed_output.append(lines[i])
                i += 1
        i += 1
    return processed_output

def print_list(output):
    for item in output:
        print(item)

def post_download(transfer_folder):
    download_folder_path = get_home_path(download_folder)
    files = os.listdir(download_folder_path)
    for file in files:
        shutil.move(f"{download_folder_path}/{file}", transfer_folder)

def get_transfer_folder(programme_type, preset):
    transfer_folder = get_home_path(generic_transfer_folder)
    if preset:
        if programme_type == "radio":
            transfer_folder = get_home_path(radio_present_transfer_folder)
        elif programme_type == "tv":
            transfer_folder = get_home_path(tv_preset_transfer_folder)
    return transfer_folder
    
def get_type_arg(programme_type):
    return f"--type={programme_type}"

def get_force_arg(force):
    arg = ""
    if force:
        arg = "--force"
    return arg

def get_output_arg():
    path = get_home_path(download_folder)
    return f"--output=\"{path}\""

def get_quality_arg(programme_type, quality):
    if not quality:
        quality = default_quality[programme_type]
    return f"--mode={quality}"

def get_since_arg(since):
    arg = ""
    if since:
        since_hours = since * 24
        arg = f"--available-since={since_hours}"
    return arg

def get_channel_arg(channel):
    arg = ""
    if channel != "all":
        arg = f"--channel=\"^{channel}$\""
    return arg

def get_preset_arg(programme_type):
    arg = ""
    preset = get_preset(programme_type)
    first = True
    for item in preset:
        if first:
            first = False
        else:
            arg += "|"
        arg += f"^{item}$"
    return arg

def get_preset(programme_type):
    if programme_type == "radio":
        return radio_preset 
    else: 
        return tv_preset

def execute(cmdline):
    if test_mode: 
        print(cmdline)
    else:
        os.system(cmdline)

def execute_with_callback(cmdline, callback):
    if test_mode: 
        print(cmdline)
        return []
    else:
        returned_output = subprocess.check_output(cmdline, shell=True)
        output = callback(returned_output.decode("utf-8"))
        return output

def acquire_lock(lock_file):
    # Only one instance of this program can run at a time
    path = Path(lock_file)
    if (path.exists()):
        print(f"An instance is already running: {lock_file}")
        sys.exit(1)
    path.touch()

def release_lock(lock_file):
    delete_file(lock_file)

def delete_file(path):
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)

def get_home_path(folder):
    home_env_value = os.environ.get('HOME', ".")
    path = os.path.join(home_env_value, folder)
    return path

def main():
    args = parse_arguments()
    acquire_lock(get_home_path(lock_file))
    if args.download: do_download(args.type, args.since, args.quality, args.force, args.pid, args.preset)
    if args.list: do_list(args.type, args.channel, args.since)
    if args.search: do_search(args.type, args.channel, args.since, args.search)
    if args.latest: do_latest(args.type, args.since)
    release_lock(get_home_path(lock_file))

if __name__ == '__main__':
    main()
    sys.exit(0)