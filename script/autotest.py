import argparse
from ast import parse
from asyncio import subprocess
from io import TextIOWrapper
from logging import warning
import random
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import subprocess
from multiprocessing import Pool
import os
import time
import json
import utils


parser = argparse.ArgumentParser(description='specify a cfg file')
parser.add_argument('-f', '--file', help='cfg file path')
args = parser.parse_args()

CFG_PATH = args.file

# check dir
cfgfile = utils.CFGReader(CFG_PATH)
commit_info_path = cfgfile['global']['log_root'] + '/commits.txt'

works, pre_work, post_work = utils.getWorks(cfgfile)
if len(works) == 0:
    print('has no work to do')
    exit(1)
# 拉取仓库并切换branch
repo = utils.getBranch(cfgfile)


if not os.path.exists(cfgfile['global']['log_root']):
    os.makedirs(cfgfile['global']['log_root'])

# 工作逻辑:获取远程commit并与当前脚本的本地测试commit比较,获取新添加的commit
# 对新添加的commit进行测试,测试完毕,等待一段时间再次获取远程commit


def mailSendMsg(msg: str):
    if cfgfile['global']['debug_mode'] == 'true':
        print(msg)
    elif cfgfile['global']['debug_mode'] == 'false' and cfgfile['mail']['enable'] == 'true':
        try:
            smtp = smtplib.SMTP()
            smtp.connect(cfgfile['mail']['mail_host'])
            smtp.login(cfgfile['mail']['mail_sender'],
                       cfgfile['mail']['mail_license'])
            for receiver in cfgfile['mail']['mail_receivers'].split(';'):
                smtp.sendmail(cfgfile['mail']['mail_sender'], receiver, msg)
            smtp.quit()
        except Exception as e:
            print(msg)
            warning("mail send fail!!,check your license and network")


def startMain(work, log_dir: str, etcArg):
    task = work[1]
    log_ = log_dir
    utils.argReplace(task, dict({'sublog': log_}, **etcArg))
    if not os.path.exists(log_):
        os.makedirs(log_)
    taskout = open(log_+'/taskout.txt', 'w')
    taskerr = open(log_+'/taskerr.txt', 'w')
    other = open(log_+'/other.txt', 'w')
    other.write('**********pre-task start**********\n')
    other.flush()
    startTime = time.time()
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
    tupTime = int(time.time()-startTime)  # 秒时间戳
    other.write(
        '**********runTime:{0}h:{1}m:{2}s**********\n'.format(tupTime // 3600, (tupTime % 3600)//60, (tupTime % 3600)%60))
    # start except-task
    if not (post and post.returncode == 0):
        other.write(
            '**********running error,except-task start**********\n')
        other.flush()
        exce = subprocess.run(args=task[3], shell=True, stdout=other,
                              stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
        other.close()
        mailSendMsg(
            """autotest find a error in:
            repo:{0} 
            branch:{1}
            work:{2}
            log:{3}
            """.format(cfgfile['global']['repo_url'],
                       cfgfile['global']['repo_branch'],
                       work[0],
                       log_
                       ))
        return False
    other.close()
    return True


def Wstart(log_dir, log_file: TextIOWrapper, etcArg: dict):
    '''
    执行pre-work
    '''
    task = pre_work.get('pre-work').copy()
    utils.argReplace(task, dict({'sublog': log_dir}, **etcArg))
    log_file.write('**********pre-work:pre-task start**********\n')
    log_file.flush()
    # pre-work:pre-task
    pre = subprocess.run(args=task[0], shell=True, stdout=log_file,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    # pre-work:task
    ret = None
    if pre.returncode == 0:
        log_file.write('**********pre-work:task start**********\n')
        log_file.flush()
        ret = subprocess.run(args=task[1], shell=True, stdout=log_file,
                             stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    if not (ret and ret.returncode == 0):
        log_file.write(
            '**********pre-work: running error,except-task start**********\n')
        log_file.flush()
        exce = subprocess.run(args=task[3], shell=True, stdout=log_file,
                              stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
        return False

    return True


def Wrun_multi(log_dir, etcArg):
    pool = Pool(processes=int(cfgfile['iteration']['max_process']))
    results = []
    work_items = list(works.items())
    cnt = 0
    for work in work_items:
        numaCores = cfgfile['work-'+work[0]].get('numacores')
        numa_args = ''
        if not numaCores:
            pass
        elif int(numaCores) > 0:
            numa_args = utils.get_numa_args(numaCores)
        random_int = random.randint(0, 10000)
        results.append(pool.apply_async(
            startMain,
            (work, log_dir+'/'+work[0],
             dict({'tid': cnt, 'random_int': random_int, 'numa': numa_args}, **etcArg))))
        cnt += 1
        if cnt >= int(cfgfile['iteration']['max_process']):
            cnt = 0
    pool.close()
    pool.join()
    finished = True
    runErr_works = []
    for cnt in range(len(results)):
        if not results[cnt].get():
            runErr_works.append(work_items[cnt][0])
            finished = False
    return finished, runErr_works


def Wrun_single(log_dir, etcArg):
    pool = Pool(processes=int(cfgfile['iteration']['max_process']))
    results = []
    work_items = list(works.items())
    cnt = 0
    names = []
    for work in work_items:
        files, sublog = utils.get_file_list(
            cfgfile['work-'+work[0]]['binpath'])
        for i in range(len(files)):
            numaCores = cfgfile['work-'+work[0]].get('numacores')
            numa_args = ''
            if not numaCores:
                pass
            elif int(numaCores) > 0:
                numa_args = utils.get_numa_args(numaCores)
            names.append(sublog[i])
            random_int = random.randint(0, 10000)
            results.append(
                pool.apply_async(
                    startMain,
                    (work,
                     log_dir+'/'+work[0]+'/'+sublog[i],
                     dict({'tid': cnt, 'random_int': random_int, 'binfile': files[i], 'numa': numa_args}, **etcArg))))
            cnt += 1
            if cnt >= int(cfgfile['iteration']['max_process']):
                cnt = 0
    pool.close()
    pool.join()
    finished = True
    runErr_works = []
    for cnt in range(len(results)):
        if not results[cnt].get():
            runErr_works.append(names[cnt])
            finished = False
    return finished, runErr_works


def Wend(work_finished, log_dir, log_file: TextIOWrapper, etcArg: dict):
    '''
    执行post-work
    '''
    task = post_work.get('post-work').copy()
    utils.argReplace(task, dict({'sublog': log_dir}, **etcArg))
    log_file.write('**********post-work:task start**********\n')
    log_file.flush()
    # post-work:task start
    ret = subprocess.run(args=task[1], shell=True, stdout=log_file,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    # post-work:post-task start
    post = None
    if ret.returncode == 0:
        log_file.write('**********post-work:post-task start**********\n')
        log_file.flush()
        post = subprocess.run(args=task[2], shell=True, stdout=log_file,
                              stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    log_file.close()
    if (not (post and post.returncode == 0)) or (not work_finished):
        subprocess.run(args=task[3], shell=True, stdout=None,
                       stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
        # 返回post-work的结果
        return (post and post.returncode == 0)
    return True

# 如果当前commit测试错误,则删除未还未测试的commit
# 用于在此产生一个断点用于下次运行时恢复运行


def breakpointSave(break_commit: dict):
    done_commits: list[dict] = []
    with open(commit_info_path, 'r') as fs:
        local_commits = json.loads(fs.read())
        for i in range(len(local_commits)-1):
            if local_commits[i]['commit'] == break_commit['commit']:
                done_commits = local_commits[i+1:]
                break
    with open(commit_info_path, 'w') as fs:
        fs.write(json.dumps(done_commits))


def iteration(extra_commits):
    extra_commits.reverse()
    # 从最老的commit开始测试
    for commit in extra_commits:
        repo.git.checkout(commit['commit'])
        commit_log_path = cfgfile['global']['log_root']+'/'+commit['commit']
        if not os.path.exists(commit_log_path):
            os.mkdir(commit_log_path)
        commit_log_file = open(commit_log_path + '/iter_log.txt', 'w')
        etcArg = {}

        error_msg = ''
        #######
        finished0 = Wstart(commit_log_path, commit_log_file, etcArg)
        finished1 = False
        if finished0:
            #######
            if cfgfile['iteration']['working_mode'] == 'multi':
                finished1, runErr_works = Wrun_multi(commit_log_path, etcArg)
            elif cfgfile['iteration']['working_mode'] == 'single':
                finished1, runErr_works = Wrun_single(commit_log_path, etcArg)
            if not finished1:
                error_msg += 'error works:{0}\n'.format(str(runErr_works))
        else:
            error_msg += 'pre-work running error\n'
        # 它会自动关闭commit_log_file
        finished2 = Wend(finished1, commit_log_path,
                         commit_log_file, etcArg)
        if not finished2:
            error_msg += 'post-work running error\n'

        if not (finished0 and finished1 and finished2):  # 发生任何错误
            # 发送消息
            mailSendMsg(
                """autotest find a error in:
            repo:{0} 
            branch:{1}
            commit:{2}
            error msg: 
            {3}
            """.format(cfgfile['global']['repo_url'],
                       cfgfile['global']['repo_branch'],
                       str(commit),
                       error_msg))
            if cfgfile['iteration']['except_mode'] == 'stop':  # 如果是stop模式则直接退出并打一个断点
                breakpointSave(commit)
                return False
            elif cfgfile['iteration']['except_mode'] == 'skip':  # 如果是skip模式则跳过当前测试,进入下次迭代
                break
            elif cfgfile['iteration']['except_mode'] == 'ignore':  # 忽略,继续执行下一个commit测试
                pass
    return True


endless = int(cfgfile['iteration']['num']) < 0
iterations = int(cfgfile['iteration']['num'])
while endless or iterations > 0:
    origin_commits = utils.getAllCommitInfo(
        repo, cfgfile['iteration']['pull'])
    extra_commits = utils.checkCommit(commit_info_path, origin_commits)

    finished = iteration(extra_commits)
    iterations -= 1
    # 保存已完成的commit
    utils.saveCommits(commit_info_path)

    if not finished:
        exit(-1)
    # 延迟
    time.sleep(eval(cfgfile['iteration']['end_delay']))
print('**********all tests finished**********')
