from rest_framework.response import Response

def success(data=None, message="success"):
    return Response({
        "status": True,
        "message": message,
        "data": data
    })

def error(message="error", code=400):
    return Response({
        "status": False,
        "message": message
    }, status=code)
