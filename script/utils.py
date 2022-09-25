import configparser
from curses.ascii import isspace
from genericpath import isdir, isfile
from logging import warning
import re
import os
import git
import subprocess
import json
import psutil
import time
import glob


class CFGReader:
    cfg_map = {'global': {}}

    def __init__(self, cfg_path) -> None:
        if not os.path.exists(cfg_path):
            print('there is no cfg file')
            exit(1)
        cfgfile = configparser.ConfigParser()
        try:
            cfgfile.read(cfg_path)
        except Exception as e:
            print(e)
            exit(-1)
        reObj = re.compile('\{[^\{.]*\}')
        # 查找段
        for section in cfgfile.sections():
            self.cfg_map.update({section: {}})
            # 查找段的每个设置
            for options in cfgfile.items(section):
                result = options[1]
                # 替换变量
                for i in reObj.findall(result):
                    rep = i[1:-1]
                    var0 = self.cfg_map['global'].get(rep)
                    if var0:
                        result = result.replace(i, var0)
                    var1 = self.cfg_map[section].get(rep)
                    if var1:
                        result = result.replace(i, var1)
                    if not (var0 or var1):
                        warning(
                            'cfgReader: [can\'t fint the var] ' + section + ":" + rep)
                self.cfg_map[section].update({options[0]: result})

    def __getitem__(self, index):
        return self.cfg_map[index]

    def items(self):
        return self.cfg_map.items()


def get_file_list(path: str):
    subpaths = path.split(';')
    files = []
    names = []
    for subpath in subpaths:
        if subpath.endswith('.paths'):
            this_files = []
            with open(subpath, 'r') as fs:
                this_files = fs.read().split('\n')
            for file in this_files:
                file = file.strip()
                if file.isspace():
                    pass
                elif not os.path.exists(file):
                    warning(f'can\'t load file:{file}')
                    exit(-1)
                else:
                    files.append(file)
                    name = file.split('/')
                    names.append(name[-3]+'-'+name[-2] +
                                 '-'+name[-1].split('.')[0])
        else:
            this_files = glob.glob(subpath)
            for file in this_files:
                files.append(file)
                names.append(os.path.split(file)[1].split('.')[0])
    return files, names


def get_free_cores(n):
    # To avoid potential conflicts, we allow CI to use SMT.
    num_logical_core = psutil.cpu_count(logical=False)
    core_usage = psutil.cpu_percent(interval=1, percpu=True)
    num_window = num_logical_core // n
    for i in range(num_window):
        window_usage = core_usage[i * n: i * n + n]
        if sum(window_usage) < 0.3 * n and True not in map(lambda x: x > 0.5, window_usage):
            return (((i * n) % 128) // 64, i * n, i * n + n - 1)
    return None


def get_numa_args(n):
    numa_args = ''
    temp_flag = False
    while True:
        numa_info = get_free_cores(int(n))
        if numa_info:
            numa_args = f"numactl -m {numa_info[0]} -C {numa_info[1]}-{numa_info[2]}"
            break
        else:
            if not temp_flag:
                temp_flag = True
                print('no free cores found. will wait for free cores')
    return numa_args


def getBranch(cfgfile):
    '''
    pull repo and checkout
    '''
    try:
        repo = git.Repo(path=cfgfile['global']['working_dir'])
    except:
        print('can\'t to load the repo,will to pull new here')
        try:
            repo = git.Repo.clone_from(
                url=cfgfile['global']['repo_url'], to_path=cfgfile['global']['working_dir'])
        except:
            print('cant find the repo,exit')
            exit(-1)
    try:
        repo.git.checkout(cfgfile['global']['repo_branch'])
    except:
        print('cant find the branch,exit')
        exit(-1)
    return repo
# return the all commit info


def getAllCommitInfo(repo: git.Repo, count: int):
    '''
    get branch's commits info:commit:hashcode,author,summary,date
    Sort by time
    '''
    commit_log = repo.git.log('--pretty={"commit":"%h","author":"%an","summary":"%s","date":"%cd"}', max_count=count,
                              date='format:%Y-%m-%d %H:%M')
    log_list = commit_log.split("\n")
    real_log_list = [eval(item) for item in log_list]
    return real_log_list


def checkCommit(commit_info_path, origin_commits):
    '''
    compare the local commits info with origin commits
    and return the extra commit
    if local is the newest ,return None
    '''
    extra_commits = []
    # init commits info
    with open(commit_info_path, 'w') as fs:
        fs.write(json.dumps(origin_commits))
    if not os.path.exists(commit_info_path+'.old'):
        return origin_commits
    ##
    local_commits = []
    # load last has done commit
    with open(commit_info_path+'.old', 'r') as fs:
        local_commits = json.loads(fs.read())

    if len(local_commits) == 0:
        return origin_commits

    for i in range(len(origin_commits)):
        if origin_commits[i]['commit'] == local_commits[0]['commit']:
            if i == 0:
                return []
            extra_commits = origin_commits[0:i]
            return extra_commits
    return origin_commits


def saveCommits(commit_info_path):
    '''
    save has finished commit
    '''
    os.rename(commit_info_path, commit_info_path+'.old')


# get cfgfile custom works
# return [[pre-task,task,post-task]]
def getWorks(cfgfile):
    pre_work: dict[str, list] = {}
    works: dict[str, list] = {}
    post_work: dict[str, list] = {}
    for work in cfgfile.items():
        if not work[1].get('pre-task'):
            work[1].update({'pre-task': ''})
        if not work[1].get('post-task'):
            work[1].update({'post-task': ''})
        if not work[1].get('except-task'):
            work[1].update({'except-task': ''})
        if work[0] == 'pre-work':
            pre_work.update({'pre-work': [work[1].get('pre-task'),
                                          work[1].get('task'),
                                          work[1].get('post-task'),
                                          work[1].get('except-task')]})
        if work[0] == 'post-work':
            post_work.update({'post-work': [work[1].get('pre-task'),
                                            work[1].get('task'),
                                            work[1].get('post-task'),
                                            work[1].get('except-task')]})
        if work[0].startswith('work-'):
            works.update({work[0][5:]: [work[1].get('pre-task'),
                                        work[1].get('task'),
                                        work[1].get('post-task'),
                                        work[1].get('except-task')]})
    return (works, pre_work, post_work)


def argReplace(coms, specArg: dict):
    reObj = re.compile('\$[^\$.]*\$')
    for i in range(len(coms)):
        if coms[i]:
            for arg in reObj.findall(coms[i]):
                rep = arg[1:-1]
                var0 = str(specArg.get(rep))
                if var0:
                    coms[i] = coms[i].replace(arg, var0)
                else:
                    warning('argReplace: [can\'t find the specarg] ' + rep)

# start one work
# return finished


def startWork(work, log_dir: str, etcArg):
    name = work[0]
    task = work[1]
    log_ = log_dir+'/'+name
    argReplace(task, dict({'sublog': log_}, **etcArg))
    if not os.path.exists(log_):
        os.mkdir(log_)

    taskout = open(log_+'/taskout.txt', 'w')
    taskerr = open(log_+'/taskerr.txt', 'w')
    other = open(log_+'/other.txt', 'w')
    other.write('**********pre-task start**********\n')
    other.flush()
    # start pre-task
    pre = subprocess.run(args=task[0], shell=True, stdout=other,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')

    # start task
    ret = None
    if pre.returncode == 0:
        ret = subprocess.run(args=task[1], shell=True, stdout=taskout,
                             stderr=taskerr, stdin=None, check=False, encoding='utf-8')
    taskout.close()
    taskerr.close()
    # start post-task
    post = None
    if ret and ret.returncode == 0:
        other.write('**********task finished,post-task start**********\n')
        other.flush()
        post = subprocess.run(args=task[2], shell=True, stdout=other,
                              stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    # start except-task
    if not (post and post.returncode == 0):
        other.write(
            '**********running error,except-task start**********\n')
        other.flush()
        exce = subprocess.run(args=task[3], shell=True, stdout=other,
                              stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
        other.close()
        return False
    other.close()
    return True
