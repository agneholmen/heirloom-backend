from .models import Tree
from django.utils.functional import SimpleLazyObject

def tree_data(request):
    if type(request.user) != SimpleLazyObject:
        trees = Tree.objects.filter(user=request.user).order_by('name')
    else:
        trees = None

    return {
        'trees': trees
    }