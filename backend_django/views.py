from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "Backend Django funcionando!"})
