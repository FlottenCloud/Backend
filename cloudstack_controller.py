import os   #여기서부터 장고와 환경을 맞추기 위한 import
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudmanager.settings")    # INSTALLED_APPS에 등록된 앱 내의 함수가 아니기 때문에, INSTALLED APPS에 있는 모듈을 임포트 할 때 필요
import django
django.setup()

import requests
import json
from django.http import JsonResponse

import base64
import hashlib
import hmac
import urllib.parse
import urllib.request

<<<<<<< HEAD
<<<<<<< HEAD
hostIP = "211.197.83.186:8080"
api_base_url = "http://211.197.83.186:8080/client/api?"
admin_apiKey = "CPS5vA56-gQ3RPyshKyzf7zc27ECdCS2dfHf-8_b8yU23r8KiqKDmZfLAnZ8bogRdcoqSFkCdmMzXPuzUyscvQ"
admin_secretKey = "Th122sV_n-GE3gyAT32uT0-ZwK5Pzku3Ti5rM0GF0SLA_9uRF_P6rWO9_85vJzs8aJDCZZtcS7FFgeq0w34i_Q"
netOfferingID_L2VLAN = "f96cc504-5219-4e88-a779-f74b96caf997"
zoneID = "5d8ba90e-a169-43d8-8742-036e795d2ccb"
domainID = "a3ac1371-34ed-11ed-914c-0800270aea06"
hostID = "ea25001b-9ca9-4c6c-9d83-af8170ca04c9"
small_offeringID = "2866ead4-8cc9-413d-a43a-08e818dfe7eb"
medium_offeringID = "ce7d7d5c-d343-4ef5-82e0-a45fd70f8c8a"
=======
hostIP = ""
api_base_url = ""
admin_apiKey = ""
admin_secretKey = ""
netOfferingID_L2VLAN = ""
zoneID = ""
domainID = ""
hostID = ""
small_offeringID = ""
medium_offeringID = ""
>>>>>>> 767073b4badb1e91b51ff26f98c7f58d902e471d
=======
hostIP = "10.125.70.28"
api_base_url = "http://10.125.70.28:8080/client/api?"
admin_apiKey = "W52i_LjFrXiTApR6FseHUkkGH24fIHnKvZ7Oq8rZQVZ8ow1TIl4JTmYIkbjmF-9_7t7zplyR-YkcWIHQIOYU9Q"
admin_secretKey = "smYL6tn_2ghP8q64qfEz8Ewq1htWcNhDlgDV3ugy53dsWZ1tjFW3LaiYU1RtpnhtzjQpfSPKk4G9MJAAWfHspQ"
netOfferingID_L2VLAN = "9b55e8b7-8a32-401e-86bc-92eeb087a02b"
zoneID = "aee60d64-ae63-4319-85f1-92687f1875ff"
domainID = "e5934522-fe91-11ec-ae65-525400c8d027"
hostID = "db1f8fad-efa5-4cdb-92e6-19ff286a2253"
small_offeringID = "6906780f-3625-46ea-86f0-5ed272dc2f73"
medium_offeringID = "9700927a-d86d-431f-a81d-3b9e6eb1be13"
>>>>>>> 3286821280d1532106a3f4ccb7b78255d8950004

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
    req = api_base_url + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req)
    urllib.request.urlcleanup()
    res = urllib.request.urlopen(req)
    response = res.read()
    
    print("클라우드 스택에서의 리스폰스:", response)
    return response

def requestThroughSigForTemplateRegist(secretKey, request_body):
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
    req = api_base_url + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req)
    
    return req


def requestThroughSigWithURL(base_url, secretKey, request_body):
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
    req = base_url + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req)
    urllib.request.urlcleanup()
    res = urllib.request.urlopen(req)
    response = res.read()

    print("클라우드 스택에서의 리스폰스:", response)
    return response

def requestThroughSigUsingRequests(secretKey, request_body):
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
    req_url = api_base_url + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req_url)
    req = requests.get(req_url)
    res = req.json()
    print("클라우드 스택에서의 리스폰스:", res)

    return res
