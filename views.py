# views.py

from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa
import datetime
from django.conf import settings

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('UTF‐8')), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def result_pdf_view(request):
    # Get results, student info etc.
    context = {
        'college_name': 'ABC University',
        'college_address': '123 Street, City, State',
        'logo_url': request.build_absolute_uri(settings.STATIC_URL + 'images/logo.png'),
        'student': {
            'name': 'John Doe',
            'roll_no': '2025XYZ123',
            'department': 'Computer Science',
            'semester': 'Odd Semester 2025'
        },
        'results': results_queryset,  # list of result dicts
        'total_marks': 450,
        'total_max_marks': 500,
        'percentage': 90,
        'cgpa': '9.0 / 10',
        'signature_url': request.build_absolute_uri(settings.STATIC_URL + 'images/signature.png'),
        'signer_name': 'Dr. Jane Smith',
        'signer_designation': 'Controller of Exams',
        'generated_on': datetime.datetime.now().strftime("%d %B, %Y %H:%M"),
        'session': '2024‐25'
    }

    pdf_response = render_to_pdf('result_pdf.html', context)
    if pdf_response:
        filename = f"Result_{context['student']['roll_no']}_{context['student']['semester']}.pdf"
        pdf_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf_response
    else:
        return HttpResponse("Error generating PDF", status=500)
