## AUTOTEST

该项目是用于对指定github仓库的分支以及各类提交进行批量测试的自动化脚本    


其主要工作过程为:       

拉取仓库并切换到指定分支        

拉取一定数量的commit并依次测试,如果有的commit已经测试完毕则不会再测试       

可以对一个commit指定多个测试work        

每个commit测试项目都有一个专门的log文件夹       

用于存放测试命令的log信息,其文件结构如下        

其中commits.txt存放待测试的commit,该文件只存在于运行时       

commit.txt.old存放上次测试完毕的commit      

它会用于与远程的commit进行比较并提取出新增加的commit进行测试        

如果某commit发生错误,则可以发送错误信息到指定邮箱用于通知

该项目使用xxx.cfg进行配置      

具体配置事项以注释的形式在temp.cfg中说明


## 项目log文件目录:
```
log_root
--[commit hash code]
    --work1
        --other.txt
        --taskout.txt
        --taskerr.txt
    --work2
        --...
    --iter_log.txt
--[commit hash code]
    --...
--commits.txt
--commits.txt.old
```

其中:
other.txt:代表每个work的pre-task,post-task,except-task输出
taskerr.txt:代表每个work的task错误输出
taskout.txt:代表每个work的task标准输出

iter_log.txt:代表当前commit测试过程中,pre-work和post-work的输出

commits.txt:代表当前迭代待测试的commit,该文件只存在于运行时
commit.txt.old:代表上次迭代已执行完毕的commit

## 使用方法

目前已配置好一个例子
输入
```
python3 script/autotest.py -f temp1.cfg
```
即可

如果要自定义测试脚本,请参考temp.cfg