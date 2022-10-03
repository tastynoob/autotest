from genericpath import isdir, isfile
import re
import os

#该脚本用于对运行好的测试进行时间排序

#测试对象运行结果的输出路径
work_dir = "/nfs/home/xuyan/autotest/workspace/log_root/97e1b5399/test-diff"
#测试对象的存放路径
binPath = "/nfs/home/share/test-workloads/test-diff-on"
#测试对象的后缀名
suffix = ".bin"
#输出文件名,会自动添加上.paths后缀
outfilename = "diff-on-bin"

other_files = {}

pattern = re.compile(
    r"\*\*\*\*\*\*\*\*\*\*runTime:(\d+)h:(\d+)m:(\d+)s\*\*\*\*\*\*\*\*\*\*")


def filepaser(filepath):
    match = ()
    with open(filepath) as fs:
        infos = fs.read().split('\n')
        for info in infos:
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
with open(outfilename+'.paths', 'w') as fs:
    for file in other_files:
        fs.write(file[0]+'\n')
