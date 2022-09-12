import base64
import hashlib
import hmac
import urllib.parse
import urllib.request


def requestThroughSig(secretKey, request_body):
    print("a")
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
    req = "http://119.198.160.6:8080/client/api?" + request_str + '&signature=' + sig
    print("클라우드 스택으로의 리퀘스트:", req)
    # res=urllib.request.urlopen(req)
    # response=res.read()

    print("시그니처:", sig)
    return sig

def main():
    # request_body = {"apiKey":"XM1kmGp-sHQOfeAYbLVtG3tPz94BNdGDdJh9qAAqh4I4OXmeSvr7piCQweWQUs9gJkhqJNTIPEccJoKJwuLtTA", "response":"json", "command":"listVirtualMachines", "id" : "f092f028-73b9-48e5-b2ea-1b0779f2308d"}
    # requestThroughSig("Zf1ErQoK-diymzPP_-T2E6AwgeAWDtFOyULcmoij8Sm0CUtwEcoOkAdTJY5EnQMSAJ2KbCW6OO-BiJ0iHTjxcg", request_body)

    request_body = {"apiKey":"XM1kmGp-sHQOfeAYbLVtG3tPz94BNdGDdJh9qAAqh4I4OXmeSvr7piCQweWQUs9gJkhqJNTIPEccJoKJwuLtTA", "response":"json", "command":"listServiceOfferings", "id" : "63fe8390-1f96-4a51-97a2-ffc55161fcad"}
    requestThroughSig("Zf1ErQoK-diymzPP_-T2E6AwgeAWDtFOyULcmoij8Sm0CUtwEcoOkAdTJY5EnQMSAJ2KbCW6OO-BiJ0iHTjxcg", request_body)
    

main()