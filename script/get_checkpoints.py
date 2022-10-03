import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time

import psutil


def load_all_gcpt(gcpt_path, json_path):
    all_gcpt = []
    with open(json_path) as f:
        data = json.load(f)
    for benchspec in data:
        for point in data[benchspec]:
            weight = data[benchspec][point]
            gcpt = os.path.join(gcpt_path, "_".join(
                [benchspec, point, weight]))
            bin_dir = os.path.join(gcpt, "0")
            bin_file = list(os.listdir(bin_dir))
            assert (len(bin_file) == 1)
            bin_path = os.path.join(bin_dir, bin_file[0])
            assert (os.path.isfile(bin_path))
            all_gcpt.append(bin_path)
    return all_gcpt


def get_ci_workloads():
    workloads = {
        "linux-hello": "bbl.bin",
        "linux-hello-smp": "bbl.bin",
        "povray": "_700480000000_.gz",
        "mcf": "_17520000000_.gz",
        "xalancbmk": "_266100000000_.gz",
        "gcc": "_39720000000_.gz",
        "namd": "_434640000000_.gz",
        "milc": "_103620000000_.gz",
        "lbm": "_140840000000_.gz",
        "gromacs": "_275480000000_.gz",
        "wrf": "_1916220000000_.gz",
        "astar": "_122060000000_.gz"
    }

    all_cpt = [
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gcb_o2_20m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gcb_o3_20m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gc_o2_20m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gc_o2_50m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gcb_o2_20m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gcb_o3_20m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gc_o2_50m/take_cpt",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_speed_rv64gcb_o3_20m/take_cpt"
    ]
    all_json = [
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gcb_o2_20m/json/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gcb_o3_20m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gc_o2_20m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec06_rv64gc_o2_50m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gcb_o2_20m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gcb_o3_20m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_rv64gc_o2_50m/simpoint_summary.json",
        "/nfs-nvme/home/share/checkpoints_profiles/spec17_speed_rv64gcb_o3_20m/simpoint_summary.json"
    ]
    assert (len(all_cpt) == len(all_json))
    # all_gcpt=[]
    # for i in range(len(all_cpt)):
    all_gcpt = load_all_gcpt(all_cpt[1], all_json[1])
    return all_gcpt


gcpts = get_ci_workloads()

with open('checkpoints.paths', 'w') as fs:
    for file in gcpts:
        fs.write(file+' 5 \n')
