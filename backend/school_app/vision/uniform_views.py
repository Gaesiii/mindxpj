from django.http import HttpResponse
from school_app.accounts.services import AccountError
from school_app.academics.services import supervisor_user, require_class
from school_app.core.api import api_view,json_response,read_json


def no_query(request):
    if request.GET:
        raise AccountError('VALIDATION_ERROR','No query parameters accepted.',422)


@api_view('GET','POST')
def uniform_profile(request,classroom_id):
    from . import uniform_services as services
    require_class(request.user,classroom_id)
    no_query(request)
    return json_response(services.profiles(request.user,classroom_id) if request.method == 'GET'
                         else services.select_profile(request.user,classroom_id,read_json(request)))


@api_view('GET','POST')
def uniform_samples(request,classroom_id):
    from . import uniform_services as services
    require_class(request.user,classroom_id)
    no_query(request)
    if request.method == 'GET':
        return json_response(services.samples(request.user,classroom_id))
    supervisor_user(request.user)
    if set(request.FILES) != {'image'} or len(request.FILES.getlist('image')) != 1 or any(len(request.POST.getlist(k)) != 1 for k in request.POST):
        raise AccountError('VALIDATION_ERROR','Submit one image and garment metadata.',422)
    return json_response(services.add_sample(request.user,classroom_id,request.FILES['image'],request.POST.dict()),201)


@api_view('GET','DELETE')
def uniform_sample_image(request,sample_id):
    from . import uniform_services as services
    sample = services.require_sample(request.user,sample_id)
    no_query(request)
    if request.method == 'DELETE':
        supervisor_user(request.user)
        if request.body:
            raise AccountError('VALIDATION_ERROR','DELETE has no body.',422)
        return json_response(services.delete_sample(request.user,sample_id))
    response = HttpResponse(bytes(sample.image),content_type='image/png')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


@api_view('GET')
def uniform_dataset_export(request,classroom_id):
    from . import uniform_services as services
    supervisor_user(request.user)
    no_query(request)
    response = HttpResponse(services.export_dataset(request.user,classroom_id),content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="uniform-dataset.zip"'
    response['Cache-Control'] = 'private, no-store'
    return response
