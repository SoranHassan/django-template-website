from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
import os


def generate_invoice_pdf(order, request=None):
    """تولید فاکتور PDF برای سفارش"""

    html_string = render_to_string('orders/invoice.html', {'order': order}, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri() if request else '/')
    pdf = html.write_pdf()
    return pdf


def generate_invoice_response(order, request=None):
    """برگرداندن فاکتور PDF به عنوان HTTP Response"""

    pdf = generate_invoice_pdf(order, request)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{order.pk}.pdf"'

    return response