import base64
import hashlib
import hmac
import urllib.parse
import urllib.request
import requests
import cloudstack_controller as csc
import openstack_controller as oc
from bs4 import BeautifulSoup

admin_apiKey = csc.admin_apiKey
admin_secretKey = csc.admin_secretKey
zoneID = csc.zoneID
domainID = csc.domainID



def requestThroughSig(secretKey, request_body):
    request_str = '&'.join(['='.join([k, urllib.parse.quote_plus(request_body[k])]) for k in request_body.keys()])
    sig_str = '&'.join(
        ['='.join([k.lower(), urllib.parse.quote_plus(request_body[k].lower().replace('+', '%20'))]) for k in
         sorted(request_body)])
    sig = hmac.new(secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1)
    sig = hmac.new(secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()
    sig = base64.encodebytes(hmac.new(secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest())
    sig = base64.encodebytes(
        hmac.new(secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()).strip()
    sig = urllib.parse.quote_plus(base64.encodebytes(
        hmac.new(secretKey.encode('utf-8'), sig_str.encode('utf-8'), hashlib.sha1).digest()).strip())
    req_url = "http://10.125.70.28:8080/client/api?" + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req_url)
    # res=urllib.request.urlopen(req)
    # response=res.read()

    header = {"sessionkey" : "6agWewdCWRPj70ceEeKfAXX85Ic"}
    req = requests.get(req_url, headers = header)
    print("리퀘스트 리스폰스: ", req.json())
    print("Status code: ", req)
    
    print("시그니처:", sig)
    return sig, req

def main():
    # request_body = {"apiKey":"XM1kmGp-sHQOfeAYbLVtG3tPz94BNdGDdJh9qAAqh4I4OXmeSvr7piCQweWQUs9gJkhqJNTIPEccJoKJwuLtTA", "response":"json", "command":"listVirtualMachines", "id" : "f092f028-73b9-48e5-b2ea-1b0779f2308d"}
    # requestThroughSig("Zf1ErQoK-diymzPP_-T2E6AwgeAWDtFOyULcmoij8Sm0CUtwEcoOkAdTJY5EnQMSAJ2KbCW6OO-BiJ0iHTjxcg", request_body)

    # request_body = {"apiKey":"XM1kmGp-sHQOfeAYbLVtG3tPz94BNdGDdJh9qAAqh4I4OXmeSvr7piCQweWQUs9gJkhqJNTIPEccJoKJwuLtTA", "response":"json", "command":"listServiceOfferings", "id" : "63fe8390-1f96-4a51-97a2-ffc55161fcad"}
    # requestThroughSig("Zf1ErQoK-diymzPP_-T2E6AwgeAWDtFOyULcmoij8Sm0CUtwEcoOkAdTJY5EnQMSAJ2KbCW6OO-BiJ0iHTjxcg", request_body)

    # request_body = {"apiKey":"TYuuU0lIvG1ukWwQ1E9qPBGr4PU3knXvJGlMK5yIWz_zhXtXhfAi2682f_a34y2MuDfOIuEb_CkE_leODskCpg", "response":"json", "command":"listVolumes", "virtualmachineid": "4d89953c-8a47-4fac-98b7-a3c7f3d5da6a"}
    # requestThroughSig("r6avM2ip3wtjXjbNgOHIoQEK6U0T1X3flclrt55RO4v-Fa6WL0NJAVDs80ZI-AeTpKN8lIUpW2fWF_aCHv3cRA", request_body)

    # request_body = {"apiKey": "TYuuU0lIvG1ukWwQ1E9qPBGr4PU3knXvJGlMK5yIWz_zhXtXhfAi2682f_a34y2MuDfOIuEb_CkE_leODskCpg", "response": "json", "command": "registerTemplate",
    #         "displaytext": "test1", "format": "qcow2", "hypervisor": "kvm",
    #         "name": "test1", "url": url, "ostypeid": osTypeid, "zoneid": zoneID}
    # requestThroughSig("r6avM2ip3wtjXjbNgOHIoQEK6U0T1X3flclrt55RO4v-Fa6WL0NJAVDs80ZI-AeTpKN8lIUpW2fWF_aCHv3cRA", request_body)

    request_body = {"apiKey" : admin_apiKey, "response": "json", "command": "listOsTypes", "keyword": "ubuntu"}
    sig, req = requestThroughSig(admin_secretKey, request_body)

    # request_body = {"apiKey": admin_apiKey, "response": "json", "command": "destroyVirtualMachine",
    #     "id": "2ad3f87f-52bc-4888-8d3a-58a1c64a5064", "expunge": "true"}
    # sig, req = requestThroughSig(admin_secretKey, request_body)
    
    # request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "registerTemplate",
    # "displaytext" : "gettest", "format" : "qcow2", "hypervisor" : "kvm",
    # "name" : "gettest", "url" : "https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img", "ostypeid" : "12bc219b-fdcb-11ec-a9c1-08002765d220", "zoneid" : zoneID}
    
    # "17174811-e4af-4889-a552-f46fe678e644"
    # request = {"apiKey": "nLQlSOVBbw9x1R2ARLNsGvZzjfz3Rg5XaLQIEW-58nrpATuIFtjuHU17BA6UWDZ4JYvEHJSnGiYMB3aZwJuz-A", "response": "json", "command": "listVirtualMachines",
    #             "name": "testhoo1"}
    # sig, response = requestThroughSig("bCElptHE2lZqwLPDEVHYJu9U_0YIrdZdFPDf6IOwett_9iRa7ZepOvLfF7udsAtibt0xJirbeY0mGr2p_ZTsjA", request)

    # sig, req = requestThroughSig(admin_secretKey, request_body)
    # print(sig, req)
    
    # image_download_req = requests.get("http://"+oc.hostIP+"/image/v2/images/0fb22472-8a62-4404-ab47-7514fa2e517d/file", headers={'X-Auth-Token' : oc.admin_token()})
    # print(image_download_req.status_code)
    # print("오픈스택에서의 이미지 다운로드에 대한 리스폰스: ", image_download_req)
    # backup_img_file = open("test.qcow2", "wb")
    # backup_img_file.write(image_download_req.content)
    # backup_img_file.close()
    # baseURL = "http://10.125.70.28:8080/client/console?"
    # user_apiKey = csc.admin_apiKey
    # user_secretKey = csc.admin_secretKey
    # # instance_pk = json.loads(request.body)["instance_pk"]
    # instance_id = "4488848a-4a4b-42b1-9324-c979d53c6f98"

    # request_body = {"vm": instance_id, "apiKey": user_apiKey, "response": "json", "cmd": "access"}
    # console_URL_req = csc.requestThroughSigWithURL(baseURL, user_secretKey, request_body)
    # htmlData = BeautifulSoup(console_URL_req, features="html.parser")
    # console_url_body = htmlData.html.frameset.frame['src']
    # console_URL = "http:" + console_url_body
    # console_URL_split = console_URL.split("/")
    # port = console_URL_split[5].split("&")
    # port[1] = "port=6060"
    # port_join = "&".join(port)
    # externalIPwithPort=csc.hostIP.split(":")
    # externalIP=externalIPwithPort[0]
    # console_URL = "http://" + externalIP + "/" + console_URL_split[3] + "/" + console_URL_split[4] + "/" + port_join
    # print("Console URL is : " + console_URL)

main()