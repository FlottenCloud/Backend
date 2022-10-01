from django.shortcuts import render

# Create your views here.
def socket_test(request):
    return render(request, 'infosender/test.html')