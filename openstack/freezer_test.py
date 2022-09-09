# import paramiko
# hostIP = "192.168.56.128"  # 김영후 집 데스크탑 공인 ip
#
# def writeTxtFile(mode, instanceid):
#     file = open("freezer_" + mode +"_template.txt", "w", encoding="UTF-8")
#     file.write('source admin-openrc.sh')                         #환경에 맞게 설정해야됨 본인 리눅스 환경
#     file.write('\nfreezer-agent --action ' + mode + ' --nova-inst-id ')
#     file.write(instanceid)
#     file.write(
#     ' --storage local --container /home/kojunsung/' + instanceid + '_backup' + ' --backup-name ' + instanceid + '_backup' + ' --mode nova --engine nova --no-incremental true')
#     file.close()
#
#
# def readTxtFile(mode):               #mode : backup, restore
#     file = open("freezer_" + mode +"_template.txt", "r", encoding="UTF-8")
#
#     data = []
#     while (1):
#         line = file.readline()
#
#         try:
#             escape = line.index('\n')
#         except:
#             escape = len(line)
#         if line:
#             data.append(line[0:escape])
#         else:
#             break
#     file.close()
#     print(data)
#     return data
#
#
# def freezerBackup(instanceid):
#     cli = paramiko.SSHClient()
#     cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#
#     server = hostIP
#     user = "kojunsung"
#     pwd = "kojunsung"
#
#     cli.connect(server, port=22, username=user, password=pwd)
#
#     writeTxtFile("backup", instanceid)
#     # # 3 try
#     commandLines = readTxtFile("backup") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
#     print(commandLines)
#
#     stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
#     lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
#     resultData = ''.join(lines)
#
#     print(resultData) # 결과 확인
#     cli.close()
#
#
# def freezerRestore(instanceid):
#     cli = paramiko.SSHClient()
#     cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#
#     server = hostIP
#     user = "kojunsung"
#     pwd = "kojunsung"
#
#     cli.connect(server, port=22, username=user, password=pwd)
#     writeTxtFile("restore", instanceid)
#
#     commandLines = readTxtFile("restore") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
#     print(commandLines)
#
#     stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
#     lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
#     resultData = ''.join(lines)
#
#     print(resultData) # 결과 확인
#     cli.close()
#
# # Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#
#     print("freezerBackup function start!!")
#
#     freezerBackup("0343eb22-760b-423d-9b63-eac8498a6419")
#
#     print ("freezerBackup function end!!")
#
#     print ( "------------------------------")
#
#     print("freezerRestore function start!!")
#
#     freezerRestore("0343eb22-760b-423d-9b63-eac8498a6419")
#
#     print("freezerRestore function end!!")
#
