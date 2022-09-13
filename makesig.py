import base64
import hashlib
import hmac
import urllib.parse
import urllib.request
import requests
import cloudstack_controller as csc

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
    req_url = "http://119.198.160.6:8080/client/api?" + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req_url)
    # res=urllib.request.urlopen(req)
    # response=res.read()

    header = {"sessionkey" : "6agWewdCWRPj70ceEeKfAXX85Ic"}
    req = requests.get(req_url, headers = header)
    print("리퀘스트 리스폰스: ", req.json())
    
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
    # sig, req = requestThroughSig("r6avM2ip3wtjXjbNgOHIoQEK6U0T1X3flclrt55RO4v-Fa6WL0NJAVDs80ZI-AeTpKN8lIUpW2fWF_aCHv3cRA", request_body)

    # request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "registerTemplate",
    # "displaytext" : "gettest", "format" : "qcow2", "hypervisor" : "kvm",
    # "name" : "gettest", "url" : "https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img", "ostypeid" : "12bc219b-fdcb-11ec-a9c1-08002765d220", "zoneid" : zoneID}

    sig, req = requestThroughSig(admin_secretKey, request_body)
    print(sig, req)
    

main()