import urllib.parse, urllib.request
import hashlib
import base64
import hmac
import requests

import cloudstack_controller
import cloudstack_controller as csc
import openstack_controller as opc
import time
import json
import openstack.updater
from openstack.openstack_modules import RequestChecker
from bs4 import BeautifulSoup
import restore


# 정지상태의 클라우드 스택 단의 백업 인스턴스를 시작.
def start_cloudstack_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "startVirtualMachine",
               "id": instance_id}
    try:
        consoleVM_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
        print(consoleVM_req)
    except Exception as e:
        print("에러 내용: ", e)
    return consoleVM_req


# 클라우드 스택단의 인스턴스가 runnging 상태일때까지 기다리기
def wait_until_cloudstack_VM_runnging(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    time.sleep(5)
    while True:
        VM_status = restore.getCloudstackVMStatus(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
        if VM_status == "Running":
            break
        else:
            print("wait until VM status Running. current status is", VM_status)
            time.sleep(3)
    print(VM_status)
    return VM_status


# 시작된 인스턴스의 콘솔 URL get
def getCloudstack_Console_URL(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    request = {"vm": instance_id, "apiKey": cloudstack_user_apiKey, "response": "json", "cmd": "access"}

    try:
        consoleURL_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
        print(consoleURL_req)
    except Exception as e:
        print("에러 내용: ", e)
    htmlData = BeautifulSoup(consoleURL_req, features="html.parser")
    console_url_body = htmlData.html.frameset.frame['src']
    console_url = "http:" + console_url_body
    print("Console URL is : \n", console_url)
    return console_url


def webBrowser_open(url):
    webBrowser_open(url)


def change_to_cloudstack_console(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    start_cloudstack_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
    wait_until_cloudstack_VM_runnging(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
    cloudstack_console_url = getCloudstack_Console_URL(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
    webBrowser_open(cloudstack_console_url)
