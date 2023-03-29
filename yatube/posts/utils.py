from django.core.paginator import Paginator

PAG_PAGE = 10


def get_paginator(request, posts):
    page_number = request.GET.get('page')
    page_obj = Paginator(posts, PAG_PAGE).get_page(page_number)
    return page_obj
