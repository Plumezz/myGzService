import subprocess

# 创建一个新的进程，运行命令 'ls'
process = subprocess.Popen(['ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# 等待命令执行完成，获取输出和错误信息
stdout, stderr = process.communicate()

# 打印输出和错误信息
print('stdout:', stdout.decode())
print('stderr:', stderr.decode())

# 获取进程的返回码
return_code = process.returncode
print('Return code:', return_code)