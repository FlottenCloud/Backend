import json
import requests
from django.http import JsonResponse

def reqCheckerWithData(method, req_url, req_header, req_data):
    try:
        if method == "post":
            req = requests.post(req_url,
                headers = {'X-Auth-Token' : req_header},
                data = req_data)
            return req

        elif method == "get":
            req = requests.get(req_url,
                headers = {'X-Auth-Token' : req_header},
                data = req_data)
            return req

        elif method == "patch":
            req = requests.patch(req_url,
                headers = {'X-Auth-Token' : req_header},
                data = req_data)
            return req

        elif method == "delete":
            req = requests.delete(req_url,
                headers = {'X-Auth-Token' : req_header},
                data = req_data)
            return req

    except Exception:
        return {"message" : "오픈스택 서버와 통신이 원활하지 않습니다."}

def reqChecker(method, req_url, req_header):
    try:
        if method == "post":
            req = requests.post(req_url,
                headers = {'X-Auth-Token' : req_header})
            return req

        elif method == "get":
            req = requests.get(req_url,
                headers = {'X-Auth-Token' : req_header})
            return req

        elif method == "patch":
            req = requests.patch(req_url,
                headers = {'X-Auth-Token' : req_header})
            return req

        elif method == "delete":
            req = requests.delete(req_url,
                headers = {'X-Auth-Token' : req_header})
            return req
        
    except Exception:
        return {"message" : "오픈스택 서버와 통신이 원활하지 않습니다."}