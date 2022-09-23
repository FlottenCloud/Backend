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

hostIP = "10.125.70.28"
api_base_url = "http://10.125.70.28:8080/client/api?"
admin_apiKey = "jon6jxtePb0AnJQpod8eLyHxSt4JxPw5GaYMOJZNLSDaTxBpmzF-eJO7zSfuRftPO7u3s8aeY_rXSZ6uQ31utg"
admin_secretKey = "V0cWfyamMvosZBHgFECE1A9xUHavmzKa3jR2xbKaw2wHYph6mwQFbINRL_6CjHQHugISb5ldipUjb7XCyZPJjg"
netOfferingID_L2VLAN = "7695b85e-0d08-4509-85fd-0e13c85baaa6"
zoneID = "62d0f942-959e-4e83-a376-363ffb8c1953"
domainID = "cb390e5f-3b29-11ed-a749-18c04de07b21"
hostID = "3378fb58-6bb9-4f76-ac3e-c19005d29885"
small_offeringID = "70f4e0d4-d3b3-4f5e-b8e0-620276ba439f"
medium_offeringID = "f2565ee9-8b63-4c0f-a7b2-0864361bebf7"

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
