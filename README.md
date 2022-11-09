## AUTOTEST

该项目是用于进行批量测试的自动化脚本    


其主要工作过程为:       

可以设置多个测试work        

每个测试都有一个专门的log文件夹       

用于存放测试命令的log信息,其文件结构如下        

该项目使用xxx.cfg进行配置      

具体配置事项以注释的形式在temp.cfg中说明


## 项目log文件目录:
```
log_root
--work1
    --other.txt
    --taskout.txt
    --taskerr.txt
--work2
    --...
--iter_log.txt
```

其中:
other.txt:代表每个work的pre-task,post-task,except-task输出
taskerr.txt:代表每个work的task错误输出
taskout.txt:代表每个work的task标准输出

iter_log.txt:代表当前commit测试过程中,pre-work和post-work的输出


## 使用方法

目前已配置好一个例子
输入
```
python3 script/autotest.py -f temp1.cfg
```
即可

如果要自定义测试脚本,请参考temp.cfg