import argparse
from asyncio import subprocess
from io import TextIOWrapper
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import subprocess
from multiprocessing import Pool
import os
import time
import json

import utils

CFG_PATH = 'autotest.cfg'

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
    os.mkdir(cfgfile['global']['log_root'])

# 工作逻辑:获取远程commit并与当前脚本的本地测试commit比较,获取新添加的commit
# 对新添加的commit进行测试,测试完毕,等待一段时间再次获取远程commit


def mailSendMsg(msg: str):
    if cfgfile['global']['debug_mode'] == 'true':
        print(msg)
    elif cfgfile['global']['debug_mode'] == 'false' and cfgfile['mail']['enable'] == 'true':
        smtp = smtplib.SMTP()
        smtp.connect(cfgfile['mail']['mail_host'])
        smtp.login(cfgfile['mail']['mail_sender'],
                   cfgfile['mail']['mail_license'])
        for receiver in cfgfile['mail']['mail_receivers'].split(';'):
            smtp.sendmail(cfgfile['mail']['mail_sender'],receiver, msg)
        smtp.quit()


def Wstart(log_dir, log_file: TextIOWrapper, etcArg: dict):
    '''
    执行pre-work
    '''
    task = pre_work.get('pre-work').copy()
    utils.argReplace(task, dict({'sublog': log_dir}, **etcArg))
    pre = subprocess.run(args=task[0], shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    ret = subprocess.run(args=task[1], shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    after_process = None
    if ret.returncode == 0:
        pass
    else:
        after_process = subprocess.run(args=task[3], shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    log_file.write('**********pre-work:pre-task start**********\n')
    log_file.write(pre.stdout)
    log_file.write('**********pre-work:task start**********\n')
    log_file.write(ret.stdout)
    if after_process:
        log_file.write(
            '**********pre-work: task running error,except-task start**********\n')
        log_file.write(after_process.stdout)
        return False
    return True


def Wrun(log_dir, etcArg):
    pool = Pool(processes=len(works))
    results = []
    work_items = list(works.items())
    for work in work_items:
        results.append(pool.apply_async(
            utils.startWork, (work, log_dir, etcArg)).get())
    pool.close()
    pool.join()
    finished = True
    runErr_works = []
    for i in range(len(results)):
        if results[i] != 0:
            runErr_works.append(work_items[i][0])
            finished = False
    return finished, runErr_works


def Wend(work_finished, log_dir, log_file: TextIOWrapper, etcArg: dict):
    '''
    执行post-work
    '''
    task = post_work.get('post-work').copy()
    utils.argReplace(task, dict({'sublog': log_dir}, **etcArg))
    ret = subprocess.run(args=task[1], shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
    log_file.write('**********post-work:task start**********\n')
    log_file.write(ret.stdout)
    if work_finished and ret.returncode == 0:
        after_process = subprocess.run(args=task[2], shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')

        log_file.write('**********post-work:post-task start**********\n')
        log_file.write(after_process.stdout)
        log_file.close()
        return True
    else:
        log_file.close()
        subprocess.run(args=task[3], shell=True, stdout=None,
                                       stderr=subprocess.STDOUT, stdin=None, check=False, encoding='utf-8')
        return False

#如果当前commit测试错误,则删除未还未测试的commit
#用于在此产生一个断点用于下次运行时恢复运行
def breakpointSave(break_commit:dict):
    done_commits: list[dict]=[]
    with open(commit_info_path, 'r') as fs:
        local_commits = json.loads(fs.read())
        for i in range(len(local_commits)-1):
            if local_commits[i]['commit'] == break_commit['commit']:
                done_commits = local_commits[i+1:]
                break
    with open(commit_info_path,'w') as fs:
        fs.write(json.dumps(done_commits))


def iteration(extra_commits):
    extra_commits.reverse()
    #从最老的commit开始测试
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
        finished2 = False
        if finished0:
            #######
            finished1, runErr_works = Wrun(commit_log_path, etcArg)

            if not finished1:
                error_msg += 'error works:{0}\n'.format(str(runErr_works))
            #######注意post-work会自动关闭commit_log_file
            finished2 = Wend(finished1, commit_log_path,
                             commit_log_file, etcArg)

            if (not finished2) and finished1:
                error_msg += 'post-work running error\n'
        else:
            commit_log_file.close()
            error_msg += 'pre-work running error\n'
        

        if not (finished0 and finished1 and finished2):#发生任何错误

            #发送消息
            mailSendMsg(
            """autotest find a error in:
            repo:{0}
            commit:{1} in branch:{2}
            error msg: 
            {3}
            """.format(cfgfile['global']['repo_url'], commit['commit'], cfgfile['global']['repo_branch'], error_msg))
            if cfgfile['iteration']['except_mode'] == 'stop':#如果是stop模式则直接退出并打一个断点
                breakpointSave(commit)
                return False
            elif cfgfile['iteration']['except_mode'] == 'skip':#如果是skip模式则跳过当前测试,进入下次迭代
                break
            elif cfgfile['iteration']['except_mode'] == 'ignore':#忽略,继续执行下一个commit测试
                pass
    return True


endless = int(cfgfile['iteration']['num']) < 0
iterations = int(cfgfile['iteration']['num'])
while endless or iterations > 0:
    origin_commits = utils.getAllCommitInfo(repo, int(cfgfile['pull']['n']))
    extra_commits = utils.checkCommit(commit_info_path, origin_commits)

    finished = iteration(extra_commits)
    iterations -= 1
    #保存已完成的commit
    utils.saveCommits(commit_info_path)

    if not finished:
        exit(-1)
    # 延迟
    time.sleep(eval(cfgfile['iteration']['end_delay']))
