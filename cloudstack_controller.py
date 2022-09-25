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
admin_apiKey = "PI0311btQwGz3ulqBBQC46IAH_AtLImwWwvsbBmkCwuyHIOLtL7UxFL_NXco6xlPJDxI9F9XmZkAxiUq39NutQ"
admin_secretKey = "h3GuIiVgETsDtFRITxDaXitvxBoLduKILaM1GU1rAm-PSLpAnHdjtHnAeONnGzBRmkXlJ2Jjddodr0Qgl9P4tg"
zoneID = "d72dbd9a-99a6-449a-97f2-ac9472c782e8"
domainID = "1925ef52-3c9c-11ed-8341-525400956326"
hostID = "eaec4dfe-2aa1-4e29-bc6d-2f4d34f436dd"
small_offeringID = "ebfae4cb-e40f-43a2-abf2-b0723571a209"
medium_offeringID = "6b5cbc70-8125-44db-b237-b0bafe04192d"
netOfferingID_L2VLAN = "33ecd693-cdd3-4dc1-9c36-b86f07255625"

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

def requestThroughSigForTemplateRegister(secretKey, request_body):
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
