import urllib.parse,urllib.request
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

#TODO
#Account bonghun- bonghun 유저의 key들
cloudstack_user_apikey="fWLe674J43JHLrlRjsB99M3qu4O--OKsTGpm_LL8tYpmKFwNNwh-ez4B_q46uWWKd5KqQmrf6mhYX7Aw30N1fg"
cloudstack_user_secretkey="dBKpA7Rd74iDVIu2jM54xi_ohwVTGD81HhtDqe1RAPg2yKuEpHHNAzb_pDgfBv37PAw3zshxELIq1OI7wZOKpg"
local_restore_image_Download_Path='C:/'
cloudstack_VM_id="e3cb8216-8bac-42c6-be82-d81b56090cde"

#TODO 클라우드스택 공인 IP, 내부 IP 로 둘다 로그인한 상태여야한다.

def stopCloudstackInstance(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    print("Stop Instance " + instance_id + " to cloudstack")
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "stopVirtualMachine",
               "id": instance_id}
    try:
        instance_stop_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
        print(instance_stop_req)
    except Exception as e:
        print("에러 내용: ", e)
    return instance_stop_req

def getCloudstackVMStatus(cloudstack_user_apiKey, cloudstack_user_secretKey,instance_id):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "listVirtualMachines",
               "id": instance_id}
    print("get status Instance " + instance_id + " to cloudstack")

    try:
        instance_status_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
        response = json.loads(instance_status_req)
        state = response["listvirtualmachinesresponse"]["virtualmachine"][0]["state"]
        print("VM state is ", state)

    except Exception as e:
        print("에러 내용: ", e)

    return state

def listvolofvm(cloudstack_user_apiKey,cloudstack_user_secretKey,instance_id):

    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "listVolumes", "virtualmachineid": instance_id}
    try:
        list_volume_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
        print("volume list  : ", list_volume_req)
    except Exception as e:
        print("에러 내용: ", e)

    return list_volume_req

def getVol_ID_of_VM(cloudstack_user_apiKey,cloudstack_user_secretKey,instance_id):
    res=listvolofvm(cloudstack_user_apiKey,cloudstack_user_secretKey,instance_id)
    res_json=json.loads(res)
    instance_id=res_json['listvolumesresponse']['volume'][1]['id']
    print("volume is ", instance_id)
    return instance_id

def getostypeofVMid(cloudstack_user_apiKey,cloudstack_user_secretKey,vmid):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "listVirtualMachines",
               "id": vmid}
    try:
        response = csc.requestThroughSig(cloudstack_user_secretKey, request)
        response = json.loads(response)
        ostypeid = response["listvirtualmachinesresponse"]["virtualmachine"][0]["ostypeid"]
        print("VM ostype is ", ostypeid)
    except Exception as e:
        print("에러 내용: ", e)

    return ostypeid

def createTemplate(cloudstack_user_apiKey,cloudstack_user_secretKey,template_name, ostypeid, volumid):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "createTemplate", "displaytext": template_name,
               "name": template_name, "ostypeid": ostypeid,
               "volumeid": volumid
               }
    try:
        response = csc.requestThroughSig(cloudstack_user_secretKey,request)
        response_json = json.loads(response)
        templateid = response_json["createtemplateresponse"]["id"]
        print("Template Create is complete. id is ", templateid)
    except Exception as e:
        print("에러 내용: ", e)

    return templateid

def updateextractable(cloudstack_user_apiKey,cloudstack_user_secretKey,template_id):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "updateTemplatePermissions",
               "id": template_id, "isextractable": "true"}
    try:
        response = csc.requestThroughSig(cloudstack_user_secretKey,request)
    except Exception as e:
        print("에러 내용: ", e)

    print(response)

def extractTemplate(cloudstack_user_apiKey,cloudstack_user_secretKey,template_id):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "extractTemplate",
               "id": template_id, "mode": "download", "zoneid": csc.zoneID}
    # signature.requestsig(baseurl, secretkey, request)
    request_str = '&'.join(['='.join([k, urllib.parse.quote_plus(request[k])]) for k in request.keys()])
    sig_str = '&'.join(
        ['='.join([k.lower(), urllib.parse.quote_plus(request[k].lower().replace('+', '%20'))]) for k in
         sorted(request)])
    sig = hmac.new(cloudstack_user_secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1)
    sig = hmac.new(cloudstack_user_secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()
    sig = base64.encodebytes(hmac.new(cloudstack_user_secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest())
    sig = base64.encodebytes(
        hmac.new(cloudstack_user_secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()).strip()
    sig = urllib.parse.quote_plus(base64.encodebytes(
        hmac.new(cloudstack_user_secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()).strip())
    req = cloudstack_controller.api_base_url + request_str + '&signature=' + sig
    # request["signature"]=sig
    print(req)
    res = requests.get(req)
    res = res.json()
    jobid = res["extracttemplateresponse"]["jobid"]
    # print(req)
    print("job id is ", jobid)

    return jobid


def queryjobresult(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id):
    try:
        request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "queryAsyncJobResult", "jobid": extract_job_id}
        response=csc.requestThroughSig(cloudstack_user_secretKey,request)
        print(response)
    except Exception as e:
        print("에러 내용: ", e)
    return response

def getTemplateDownURL(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id):
    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "queryAsyncJobResult", "jobid": extract_job_id}
    try:
        response=csc.requestThroughSig(cloudstack_user_secretKey,request)
        resJson = json.loads(response)
        url = resJson['queryasyncjobresultresponse']['jobresult']['template']['url']
        print("DownloadURL is : \n", url)
    except Exception as e:
        print("에러 내용: ", e)

    return url

def getTemplatestatus(template_name):
    baseurl=csc.api_base_url
    apiKey = csc.admin_apiKey
    secretKey = csc.admin_secretKey

    # baseurl='http://10.125.70.28:8080/client/api?'
    request = {}
    request['command'] = 'listTemplates'
    request['templatefilter'] = 'selfexecutable'
    request['name'] = template_name
    request['response'] = 'json'
    request['apikey'] = apiKey
    secretkey = secretKey
    response = csc.requestThroughSig(secretkey,request)
    jsonData = json.loads(response)
    status = jsonData["listtemplatesresponse"]["template"][0]["status"]
    print("Template status is ", status)
    return status



def cloudstack_delete_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):

    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "destroyVirtualMachine",
               "id": instance_id, "expunge": "true"}
    response = csc.requestThroughSig(cloudstack_user_secretKey, request)
    return response

def cloudstack_delete_Template(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id):


    request = {"apiKey": cloudstack_user_apiKey, "response": "json", "command": "deleteTemplate",
               "id": template_id}

    response = csc.requestThroughSig(cloudstack_user_secretKey, request)
    return response

#TODO : 시스템 DB에서 백업한 인스턴스의 user_api,secret key ,VM ID 가져오기.




def restore(cloudstack_user_apiKey,cloudstack_user_secretKey,instance_id,cloudstack_template_name):


    #------------------------------------Cloudstack -------------------------------

    #After migration

    # 1. 실행중인 VM을 중지
    stopCloudstackInstance(cloudstack_user_apiKey,cloudstack_user_secretKey,instance_id)

    while True :
        VM_status=getCloudstackVMStatus(cloudstack_user_apiKey, cloudstack_user_secretKey,instance_id)
        if VM_status== "Stopped": break
        else :
            print("wait until VM status Stopped. current status is", VM_status)
            time.sleep(5)

    # 2. VM으로부터 템플릿 생성
    volumid = getVol_ID_of_VM(cloudstack_user_apiKey, cloudstack_user_secretKey,instance_id)
    ostypeid = getostypeofVMid(cloudstack_user_apiKey, cloudstack_user_secretKey,instance_id)
    template_name = cloudstack_template_name

    template_id =createTemplate(csc.admin_apiKey,csc.admin_secretKey,template_name, ostypeid, volumid)
    time.sleep(10)

    while True:
        template_status = openstack.updater.getTemplatestatus(csc.admin_apiKey,csc.admin_secretKey,template_name)
        if template_status == "Download Complete":
            break
        else:
            if template_status == "error":
                print("image status is error. terminate process.")
                exit()
            else:
                print("wait until image status active. current status is", template_status)
                time.sleep(3)


    # 3. 템플릿을 extractable 상태로 업데이트

    updateextractable(cloudstack_user_apiKey,cloudstack_user_secretKey,template_id)

    # 4. 템플릿 extrat api 실행

    extract_job_id = extractTemplate(cloudstack_user_apiKey,cloudstack_user_secretKey,template_id)
    while True:
        job_status = queryjobresult(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id)
        job_status = json.loads(job_status)
        job_status = job_status["queryasyncjobresultresponse"]["jobstatus"]
        if job_status == 1:
            break
        else:
            print("wait until job status active. current status is", job_status)
            time.sleep(1)

    # 5. 해당 extract job을 참조하여 download url 받아오기

    Cloudstack_Down_url=getTemplateDownURL(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id)

    res=requests.get(Cloudstack_Down_url)
    print("request get result : ",res)

    # file = open(local_restore_image_Download_Path + template_name + '.qcow2', 'wb')
    # file.write(res.content)
    # file.close()
    file=res.content
    print("image file download response is", res)

    openstackimageupload(template_name,file)

    cloudstack_delete_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
    cloudstack_delete_Template(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id)

    return res


    #------------------------------------Openstack -------------------------------

def openstackimageupload(template_name,template_file):
    import openstack_controller as oc  # import는 여기 고정 -> 컴파일 시간에 circular import 때문에 걸려서
    openstack_hostIP = oc.hostIP
    admin_token = oc.admin_token()
    req_checker = RequestChecker()
    image_create_payload = {
        "container_format": "bare",
        "disk_format": "qcow2",
        "name": template_name,
        "visibility": "public",
        "protected": False
    }
    create_req=req_checker.reqCheckerWithData("post", "http://" + openstack_hostIP + "/image/v2/images", admin_token,
                                                json.dumps(image_create_payload))

    if create_req == None:
        raise requests.exceptions.Timeout
    header=create_req.headers
    location=header["Location"]
    imageid=location.split("/")[5]
    print("image is is :",imageid)


    print("wait 5 seconds for upload binary data...")
    time.sleep(5)

    # file = open('C:/Users/PC/Desktop/os_image/backup/' + 'backup0903' + '.qcow2', 'rb')
    # file= open(local_restore_image_Download_Path + template_name + '.qcow2','rb')
    file=template_file
    # contents=file.read()
    # imageData_put_payload =contents
    imageData_put_payload=file
    # put_req=req_checker.reqCheckerWithData("put", "http://" + openstack_hostIP + "/image/v2/images/"+imageid+"/file", admin_token,
    #                                             imageData_put_payload)
    put_req=requests.put("http://" + openstack_hostIP + "/image/v2/images/"+imageid+"/file",
                         data=imageData_put_payload,headers={'X-Auth-Token' : admin_token,'Content-type': 'application/octet-stream'})
    if put_req == None:
        raise requests.exceptions.Timeout
    print(put_req)
    # file.close()


restore(cloudstack_user_apikey,cloudstack_user_secretkey,cloudstack_VM_id,"restore-bonghun")
# openstackimageupload("restore-selab")
# getVol_ID_of_VM(csc.admin_apiKey,csc.admin_secretKey,cloudstack_VM_id)