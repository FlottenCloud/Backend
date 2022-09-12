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

hostIP = "119.198.160.6:8080"
api_base_url = "http://119.198.160.6:8080/client/api?"
admin_apiKey = "TYuuU0lIvG1ukWwQ1E9qPBGr4PU3knXvJGlMK5yIWz_zhXtXhfAi2682f_a34y2MuDfOIuEb_CkE_leODskCpg"
admin_secretKey = "r6avM2ip3wtjXjbNgOHIoQEK6U0T1X3flclrt55RO4v-Fa6WL0NJAVDs80ZI-AeTpKN8lIUpW2fWF_aCHv3cRA"
netOfferingID_L2VLAN = "531f8f15-82c1-4f8e-a6ae-f4c3a3ddf1bf"
zoneID = "d4459ac7-c548-401e-a526-8ed1aad2ed54"
domainID = "93e67a39-fdca-11ec-a9c1-08002765d220"
hostID = "43428506-a50d-4ffe-a7c8-997ff548b464"
small_offeringID = "63fe8390-1f96-4a51-97a2-ffc55161fcad"
medium_offeringID = "979e5e2c-1de0-4655-b3aa-5ec1bf3907d6"

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
    
    print("클라우드 스택으로의 리스폰스:", response)
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