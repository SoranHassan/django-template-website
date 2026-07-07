from django import template

register = template.Library()

# This line just forces loading of static tag
from django.templatetags.static import static