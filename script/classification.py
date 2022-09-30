from genericpath import isdir, isfile
import re
import os

work_dir = "/media/lurker/CACHE/forLinux/openxiangshan/autotest/workspace/log_root/6248ade/test-diff"
binPath = "/media/lurker/CACHE/forLinux/openxiangshan/autotest/test"
suffix = ".bin"
outfilename = "bintest"

other_files = {}

pattern = re.compile(
    r"\*\*\*\*\*\*\*\*\*\*runTime:(\d+)h:(\d+)m:(\d+)s\*\*\*\*\*\*\*\*\*\*")

def filepaser(filepath):
    match = ()
    with open(filepath) as fs:
        infos = fs.read().split('\n')
        for info in infos :
            info = info.strip()
            if info.startswith('**********runTime:'):
                match = pattern.match(info).groups()
    time = int(match[0])*3600 + int(match[1])*60 + int(match[2])
    return time


def find_otherfile(path: dir):
    subpaths = os.listdir(path)
    for subpath in subpaths:
        subpath = os.path.join(path, subpath)

        if os.path.isdir(subpath):
            find_otherfile(subpath)
        if os.path.isfile(subpath) and subpath.endswith('other.txt'):
            ser = subpath.split(work_dir)[-1].count('/')-1
            binfile = binPath + \
                subpath.split(work_dir)[-1].split('/other.txt')[0] + suffix
            time = filepaser(subpath)
            other_files.update({binfile + ' '+str(ser): time})


find_otherfile(work_dir)
other_files = sorted(other_files.items(), key=lambda x: x[1], reverse=True)
with open(outfilename+'.paths','w') as fs:
    for file in other_files:
        fs.write(file[0]+'\n')
